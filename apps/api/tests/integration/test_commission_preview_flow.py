"""A prévia do cadastro tem que devolver o mesmo número que o motor paga.

O valor deste teste não é conferir a aritmética — disso já cuidam os testes de
domínio. É provar que prévia e cálculo efetivo não se separaram: se alguém
mexer nas faixas, na exceção individual ou no arredondamento de um lado só,
aqui quebra.
"""

from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient

from app.platform.config.security import CSRF_COOKIE, CSRF_HEADER

pytestmark = pytest.mark.integration

PDF = b"%PDF-1.4 comprovante"


async def _login(cliente: AsyncClient, admin_semeado: dict[str, str]) -> dict[str, str]:
    entrou = await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )
    assert entrou.status_code == 200, entrou.text
    return {CSRF_HEADER: cliente.cookies[CSRF_COOKIE]}


async def _consultor(cliente: AsyncClient, csrf: dict[str, str], papel: str, documento: str) -> int:
    empresa = await cliente.post(
        "/api/v1/companies",
        json={"legal_name": f"Empresa {papel}", "trade_name": papel},
        headers=csrf,
    )
    colaborador = await cliente.post(
        "/api/v1/collaborators",
        json={
            "company_id": empresa.json()["id"],
            "unit_id": None,
            "full_name": f"Consultor {papel}",
            "document": documento,
            "tax_regime": "MEI",
            "roles": [{"role": papel, "valid_from": "2026-01-01"}],
        },
        headers=csrf,
    )
    assert colaborador.status_code == 201, colaborador.text
    return int(colaborador.json()["id"])


async def test_previa_do_consultor_padrao_bate_com_a_comissao_efetivamente_creditada(
    cliente: AsyncClient,
    novo_cliente: Callable[[], AsyncClient],
    admin_semeado: dict[str, str],
) -> None:
    csrf = await _login(cliente, admin_semeado)
    consultor = await _consultor(cliente, csrf, "CONSULTOR", "529.982.247-25")

    # TPS de 30% cai na faixa de 10% do rule set inicial
    previa = await cliente.post(
        "/api/v1/commission-preview",
        json={
            "consultant_id": consultor,
            "business_date": "2026-08-12",
            "operation_amount": "10000.00",
            "tps_percentage": "30",
        },
        headers=csrf,
    )
    assert previa.status_code == 200, previa.text
    corpo: dict[str, Any] = previa.json()
    assert corpo["company_commission_amount"] == "3000.00"
    assert corpo["strategy"] == "STANDARD_CONSULTANT"
    # padrão não depende de acumulado: a prévia é exata, não estimativa
    assert corpo["estimate"] is False
    assert corpo["note"] is None

    financeiro = await cliente.post(
        "/api/v1/users",
        json={
            "email": "fin.previa@rfbalance.local",
            "full_name": "Financeiro da Prévia",
            "roles": ["FINANCEIRO"],
        },
        headers=csrf,
    )
    conta = await cliente.post(
        "/api/v1/receiving-accounts",
        json={"label": "Conta da prévia (SANTANDER)"},
        headers=csrf,
    )
    assert conta.status_code == 201, conta.text

    proposta = await cliente.post(
        "/api/v1/proposals",
        json={
            "consultant_id": consultor,
            "business_date": "2026-08-12",
            "customer_name": "Cliente da Prévia",
            "customer_document": "111.444.777-35",
            "operation_amount": "10000.00",
            "tps_percentage": "30",
        },
        headers=csrf,
    )
    assert proposta.status_code == 201, proposta.text
    assert proposta.json()["company_commission_amount"] == corpo["company_commission_amount"]

    async with novo_cliente() as outro:
        entrou = await outro.post(
            "/api/v1/auth/login",
            json={
                "email": "fin.previa@rfbalance.local",
                "password": financeiro.json()["temporary_password"],
            },
        )
        assert entrou.status_code == 200, entrou.text
        csrf_fin = {CSRF_HEADER: outro.cookies[CSRF_COOKIE]}

        declarado = await outro.post(
            f"/api/v1/proposals/{proposta.json()['id']}/receipts",
            data={
                "amount": "3000.00",
                "business_date": "2026-08-12",
                "payment_method": "PIX",
                "receiving_account_id": str(conta.json()["id"]),
            },
            files={"proof": ("c.pdf", PDF, "application/pdf")},
            headers={**csrf_fin, "Idempotency-Key": "previa-padrao"},
        )
        assert declarado.status_code == 201, declarado.text

        # enviar é ato de quem cadastra; o Financeiro não tem proposals:write
        enviada = await cliente.post(
            f"/api/v1/proposals/{proposta.json()['id']}/submission",
            json={"version": proposta.json()["version"]},
            headers=csrf,
        )
        assert enviada.status_code == 200, enviada.text
        aprovada = await outro.post(
            f"/api/v1/proposals/{proposta.json()['id']}/decision",
            json={"version": enviada.json()["version"], "decision": "APROVAR"},
            headers=csrf_fin,
        )
        assert aprovada.status_code == 200, aprovada.text

        memoria = await outro.get(
            f"/api/v1/proposals/{proposta.json()['id']}/commission-calculations"
        )
        assert memoria.status_code == 200, memoria.text
        do_consultor = [
            item
            for item in memoria.json()["items"]
            if item["strategy"] == "STANDARD_CONSULTANT" and item["beneficiary_id"] == consultor
        ]
        assert do_consultor, memoria.text
        creditado = sum(
            Decimal(entry["amount"])
            for item in do_consultor
            for entry in item["entries"]
            if entry["entry_type"] == "CREDIT"
        )

    # o que a tela mostrou antes de salvar é o que o motor creditou
    assert str(creditado) == corpo["consultant_commission_amount"]


async def test_previa_do_escalonado_vem_marcada_como_estimativa(
    cliente: AsyncClient, admin_semeado: dict[str, str]
) -> None:
    csrf = await _login(cliente, admin_semeado)
    consultor = await _consultor(cliente, csrf, "CONSULTOR_MEI_ESCALONADO", "390.533.447-05")

    previa = await cliente.post(
        "/api/v1/commission-preview",
        json={
            "consultant_id": consultor,
            "business_date": "2026-08-12",
            "operation_amount": "10000.00",
            "tps_percentage": "30",
        },
        headers=csrf,
    )
    assert previa.status_code == 200, previa.text
    assert previa.json()["strategy"] == "SCALED_CONSULTANT"
    assert previa.json()["estimate"] is True
    assert "produção acumulada" in previa.json()["note"]


async def test_previa_avisa_quando_nao_ha_funcao_de_consultor_vigente(
    cliente: AsyncClient, admin_semeado: dict[str, str]
) -> None:
    csrf = await _login(cliente, admin_semeado)
    bko = await _consultor(cliente, csrf, "BKO", "168.995.350-09")

    previa = await cliente.post(
        "/api/v1/commission-preview",
        json={
            "consultant_id": bko,
            "business_date": "2026-08-12",
            "operation_amount": "10000.00",
            "tps_percentage": "30",
        },
        headers=csrf,
    )
    assert previa.status_code == 200, previa.text
    # a comissão da empresa continua valendo: ela não depende do consultor
    assert previa.json()["company_commission_amount"] == "3000.00"
    assert previa.json()["consultant_commission_amount"] is None
    assert "não tem função de consultor vigente" in previa.json()["note"]
