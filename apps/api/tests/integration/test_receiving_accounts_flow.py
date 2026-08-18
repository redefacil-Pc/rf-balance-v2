"""Catálogo de contas que recebem o dinheiro do cliente.

Cobre o cadastro em si e o que ele existe para servir: escolher, no lançamento
do recebimento, em qual conta o valor caiu.
"""

from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient

from app.platform.config.security import CSRF_COOKIE, CSRF_HEADER

pytestmark = pytest.mark.integration


async def _login(cliente: AsyncClient, admin_semeado: dict[str, str]) -> dict[str, str]:
    entrou = await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )
    assert entrou.status_code == 200, entrou.text
    return {CSRF_HEADER: cliente.cookies[CSRF_COOKIE]}


async def test_cadastro_ordena_recusa_duplicata_e_desativa(
    cliente: AsyncClient, admin_semeado: dict[str, str]
) -> None:
    csrf = await _login(cliente, admin_semeado)

    # sem ordem informada, cada conta entra no fim da lista
    primeira = await cliente.post(
        "/api/v1/receiving-accounts",
        json={"label": "Almeida Serviços LTDA (SANTANDER)"},
        headers=csrf,
    )
    assert primeira.status_code == 201, primeira.text
    assert primeira.json()["display_order"] == 1
    assert primeira.json()["is_active"] is True

    segunda = await cliente.post(
        "/api/v1/receiving-accounts",
        json={"label": "Conta PF Fábio (BRADESCO)"},
        headers=csrf,
    )
    assert segunda.json()["display_order"] == 2

    # rótulo repetido tornaria a escolha ambígua na hora de lançar
    repetida = await cliente.post(
        "/api/v1/receiving-accounts",
        json={"label": "Almeida Serviços LTDA (SANTANDER)"},
        headers=csrf,
    )
    assert repetida.status_code == 409, repetida.text

    # a ordem manda na listagem, não a data de cadastro
    reordenada = await cliente.put(
        f"/api/v1/receiving-accounts/{segunda.json()['id']}",
        json={"label": "Conta PF Fábio (BRADESCO)", "display_order": 0},
        headers=csrf,
    )
    assert reordenada.status_code == 200, reordenada.text
    listadas = await cliente.get("/api/v1/receiving-accounts")
    assert [item["label"] for item in listadas.json()] == [
        "Conta PF Fábio (BRADESCO)",
        "Almeida Serviços LTDA (SANTANDER)",
    ]

    # desativada sai da escolha, mas continua no cadastro
    desativada = await cliente.put(
        f"/api/v1/receiving-accounts/{segunda.json()['id']}/status",
        json={"is_active": False},
        headers=csrf,
    )
    assert desativada.json()["is_active"] is False
    ativas = await cliente.get("/api/v1/receiving-accounts", params={"only_active": True})
    assert [item["label"] for item in ativas.json()] == ["Almeida Serviços LTDA (SANTANDER)"]
    todas = await cliente.get("/api/v1/receiving-accounts")
    assert len(todas.json()) == 2


async def test_recebimento_grava_a_conta_escolhida_e_recusa_conta_inativa(
    cliente: AsyncClient,
    novo_cliente: Callable[[], AsyncClient],
    admin_semeado: dict[str, str],
) -> None:
    csrf = await _login(cliente, admin_semeado)
    conta = await cliente.post(
        "/api/v1/receiving-accounts",
        json={"label": "Rede Fácil Crédito LTDA (SANTANDER)"},
        headers=csrf,
    )
    conta_id = conta.json()["id"]

    empresa = await cliente.post(
        "/api/v1/companies",
        json={"legal_name": "Rede Facil LTDA", "trade_name": "Rede Facil"},
        headers=csrf,
    )
    consultor = await cliente.post(
        "/api/v1/collaborators",
        json={
            "company_id": empresa.json()["id"],
            "unit_id": None,
            "full_name": "Consultora da Conta",
            "document": "529.982.247-25",
            "tax_regime": "CLT",
            "roles": [{"role": "CONSULTOR", "valid_from": "2026-01-01"}],
        },
        headers=csrf,
    )
    financeiro = await cliente.post(
        "/api/v1/users",
        json={
            "email": "fin.conta@rfbalance.local",
            "full_name": "Financeiro da Conta",
            "roles": ["FINANCEIRO"],
        },
        headers=csrf,
    )
    assert financeiro.status_code == 201, financeiro.text

    proposta = await cliente.post(
        "/api/v1/proposals",
        json={
            "consultant_id": consultor.json()["id"],
            "business_date": "2026-08-12",
            "customer_name": "Cliente da Conta",
            "customer_document": "111.444.777-35",
            "operation_amount": "10000.00",
            "tps_percentage": "10",
        },
        headers=csrf,
    )
    assert proposta.status_code == 201, proposta.text

    # o Financeiro é quem pode lançar; o admin não passa no portão de perfil
    async with novo_cliente() as outro:
        entrou = await outro.post(
            "/api/v1/auth/login",
            json={
                "email": "fin.conta@rfbalance.local",
                "password": financeiro.json()["temporary_password"],
            },
        )
        assert entrou.status_code == 200, entrou.text
        csrf_fin = {CSRF_HEADER: outro.cookies[CSRF_COOKIE]}

        declarado = await _declarar(outro, csrf_fin, proposta.json()["id"], conta_id, "conta-ok")
        assert declarado.status_code == 201, declarado.text

        listados = await outro.get(
            "/api/v1/receipts", params={"proposal_id": proposta.json()["id"]}
        )
        item: dict[str, Any] = listados.json()["items"][0]
        assert item["receiving_account_id"] == conta_id
        assert item["receiving_account_label"] == "Rede Fácil Crédito LTDA (SANTANDER)"

        # conta desativada não aceita lançamento novo
        await cliente.put(
            f"/api/v1/receiving-accounts/{conta_id}/status",
            json={"is_active": False},
            headers=csrf,
        )
        recusado = await _declarar(
            outro, csrf_fin, proposta.json()["id"], conta_id, "conta-inativa"
        )
        assert recusado.status_code == 422, recusado.text
        assert "ativa" in recusado.json()["detail"].lower()


async def _declarar(
    cliente: AsyncClient,
    csrf: dict[str, str],
    proposal_id: int,
    conta_id: int,
    chave: str,
) -> Any:
    return await cliente.post(
        f"/api/v1/proposals/{proposal_id}/receipts",
        data={
            "amount": "100.00",
            "business_date": "2026-08-12",
            "payment_method": "PIX",
            "receiving_account_id": str(conta_id),
        },
        files={"proof": ("comprovante.pdf", b"%PDF-1.4 comprovante", "application/pdf")},
        headers={**csrf, "Idempotency-Key": chave},
    )
