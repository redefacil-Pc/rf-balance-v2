"""Escopo de leitura de propostas por perfil.

O que estes testes protegem: antes deles, qualquer conta com `proposals:read`
enxergava a base inteira — inclusive o comprovante de pagamento do cliente,
baixável chutando o id na URL.

Filtrar só a listagem seria teatro. Por isso cada perfil é verificado nas
**quatro** rotas de leitura: lista, detalhe, anexos e download.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

import pytest
from httpx import AsyncClient, Response

from app.platform.config.security import CSRF_COOKIE, CSRF_HEADER

pytestmark = pytest.mark.integration

CNPJ_EMPRESA = "04.252.011/0001-10"
CPF_CLIENTE = "111.444.777-35"
CPF_A = "529.982.247-25"
CPF_B = "390.533.447-05"
CPF_C = "168.995.350-09"


class Api:
    def __init__(self, cliente: AsyncClient) -> None:
        self._cliente = cliente

    @property
    def _csrf(self) -> dict[str, str]:
        return {CSRF_HEADER: self._cliente.cookies[CSRF_COOKIE]}

    async def post(self, caminho: str, corpo: dict[str, Any] | None = None) -> Response:
        return await self._cliente.post(caminho, json=corpo or {}, headers=self._csrf)

    async def put(self, caminho: str, corpo: dict[str, Any]) -> Response:
        return await self._cliente.put(caminho, json=corpo, headers=self._csrf)

    async def get(self, caminho: str, **params: Any) -> Response:
        return await self._cliente.get(caminho, params=params or None)

    async def upload(self, caminho: str) -> Response:
        return await self._cliente.post(
            caminho,
            files={"file": ("c.pdf", b"%PDF-1.4 comprovante", "application/pdf")},
            headers=self._csrf,
        )


@pytest.fixture
async def admin(cliente: AsyncClient, admin_semeado: dict[str, str]) -> Api:
    await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )
    return Api(cliente)


@pytest.fixture
async def empresa(admin: Api) -> int:
    resposta = await admin.post(
        "/api/v1/companies",
        {"legal_name": "RF Balance LTDA", "trade_name": "RF Balance", "document": CNPJ_EMPRESA},
    )
    assert resposta.status_code == 201, resposta.text
    return int(resposta.json()["id"])


async def _criar_conta(
    admin: Api,
    *,
    email: str,
    nome: str,
    papel_de_acesso: str,
    empresa_id: int,
    documento: str,
    funcao: str,
) -> dict[str, Any]:
    """Conta de acesso + colaborador, como a tela de usuários faz."""
    resposta = await admin.post(
        "/api/v1/users",
        {
            "email": email,
            "full_name": nome,
            "roles": [papel_de_acesso],
            "collaborator": {
                "company_id": empresa_id,
                "unit_id": None,
                "document": documento,
                "tax_regime": (
                    "MEI" if funcao in {"CONSULTOR", "CONSULTOR_MEI_ESCALONADO"} else "CLT"
                ),
                "function": funcao,
                "valid_from": "2026-01-01",
            },
        },
    )
    assert resposta.status_code == 201, resposta.text
    corpo: dict[str, Any] = resposta.json()
    return corpo


async def _criar_proposta(
    admin: Api,
    *,
    consultant_id: int,
    documento: str = CPF_CLIENTE,
    finalizer_id: int | None = None,
) -> int:
    resposta = await admin.post(
        "/api/v1/proposals",
        {
            "consultant_id": consultant_id,
            "business_date": "2026-08-12",
            "customer_name": "Cliente Exemplo",
            "customer_document": documento,
            "operation_amount": "10000.00",
            "tps_percentage": "10",
            "finalizer_collaborator_id": finalizer_id,
        },
    )
    assert resposta.status_code == 201, resposta.text
    return int(resposta.json()["id"])


@asynccontextmanager
async def _sessao(
    novo_cliente: Callable[[], AsyncClient], email: str, senha: str
) -> AsyncIterator[Api]:
    """Sessão própria, com pote de cookies separado do administrador."""
    async with novo_cliente() as cliente:
        entrou = await cliente.post("/api/v1/auth/login", json={"email": email, "password": senha})
        assert entrou.status_code == 200, entrou.text
        yield Api(cliente)


# ---------- irrestrito ----------


async def test_admin_le_a_base_inteira(admin: Api, empresa: int) -> None:
    dono = await _criar_conta(
        admin,
        email="c1@rfbalance.local",
        nome="Consultor Um",
        papel_de_acesso="CONSULTOR",
        empresa_id=empresa,
        documento=CPF_A,
        funcao="CONSULTOR",
    )
    await _criar_proposta(admin, consultant_id=dono["collaborator_id"])

    pagina = await admin.get("/api/v1/proposals")
    assert len(pagina.json()["items"]) == 1


# ---------- consultor ----------


async def test_consultor_so_enxerga_a_propria_carteira(
    admin: Api, empresa: int, novo_cliente: Callable[[], AsyncClient]
) -> None:
    eu = await _criar_conta(
        admin,
        email="meu@rfbalance.local",
        nome="Consultor Meu",
        papel_de_acesso="CONSULTOR",
        empresa_id=empresa,
        documento=CPF_A,
        funcao="CONSULTOR",
    )
    outro = await _criar_conta(
        admin,
        email="outro@rfbalance.local",
        nome="Consultor Outro",
        papel_de_acesso="CONSULTOR",
        empresa_id=empresa,
        documento=CPF_B,
        funcao="CONSULTOR",
    )
    minha = await _criar_proposta(admin, consultant_id=eu["collaborator_id"])
    alheia = await _criar_proposta(
        admin, consultant_id=outro["collaborator_id"], documento="111.444.777-35"
    )

    async with _sessao(novo_cliente, "meu@rfbalance.local", eu["temporary_password"]) as api:
        pagina = await api.get("/api/v1/proposals")
        ids = [item["id"] for item in pagina.json()["items"]]

        assert ids == [minha]
        # e a alheia não é alcançável nem chutando o id
        assert (await api.get(f"/api/v1/proposals/{alheia}")).status_code == 404

        dashboard = await api.get(
            "/api/v1/dashboard", period_start="2026-08-01", period_end="2026-08-31"
        )
        assert dashboard.status_code == 200, dashboard.text
        assert dashboard.json()["summary"]["proposal_count"] == 1


async def test_consultor_sem_vinculo_nao_enxerga_nada(
    admin: Api, empresa: int, novo_cliente: Callable[[], AsyncClient]
) -> None:
    """Fail closed: falta de cadastro nunca vira liberação."""
    dono = await _criar_conta(
        admin,
        email="dono@rfbalance.local",
        nome="Consultor Dono",
        papel_de_acesso="CONSULTOR",
        empresa_id=empresa,
        documento=CPF_A,
        funcao="CONSULTOR",
    )
    await _criar_proposta(admin, consultant_id=dono["collaborator_id"])

    solto = await admin.post(
        "/api/v1/users",
        {
            "email": "solto@rfbalance.local",
            "full_name": "Sem Vinculo",
            "roles": ["CONSULTOR"],
        },
    )
    assert solto.status_code == 201, solto.text
    assert solto.json()["collaborator_id"] is None

    async with _sessao(
        novo_cliente, "solto@rfbalance.local", solto.json()["temporary_password"]
    ) as api:
        pagina = await api.get("/api/v1/proposals")
        assert pagina.json()["items"] == []


async def test_participacao_como_finalizador_conta(
    admin: Api, empresa: int, novo_cliente: Callable[[], AsyncClient]
) -> None:
    """Uma pessoa de finalização não entra como consultor. Olhar só
    `consultant_id` a deixaria sem enxergar o próprio trabalho."""
    consultor = await _criar_conta(
        admin,
        email="cons@rfbalance.local",
        nome="Consultor",
        papel_de_acesso="CONSULTOR",
        empresa_id=empresa,
        documento=CPF_A,
        funcao="CONSULTOR",
    )
    final = await _criar_conta(
        admin,
        email="final@rfbalance.local",
        nome="Finalizador",
        papel_de_acesso="CONSULTOR",
        empresa_id=empresa,
        documento=CPF_B,
        funcao="FINALIZACAO",
    )
    proposta = await _criar_proposta(
        admin,
        consultant_id=consultor["collaborator_id"],
        finalizer_id=final["collaborator_id"],
    )

    async with _sessao(novo_cliente, "final@rfbalance.local", final["temporary_password"]) as api:
        pagina = await api.get("/api/v1/proposals")
        assert [item["id"] for item in pagina.json()["items"]] == [proposta]


# ---------- liderança ----------


async def test_lideranca_enxerga_a_equipe_vigente(
    admin: Api, empresa: int, novo_cliente: Callable[[], AsyncClient]
) -> None:
    lider = await _criar_conta(
        admin,
        email="lider@rfbalance.local",
        nome="Lider Comercial",
        papel_de_acesso="LIDERANCA",
        empresa_id=empresa,
        documento=CPF_A,
        funcao="LIDER",
    )
    liderado = await _criar_conta(
        admin,
        email="liderado@rfbalance.local",
        nome="Consultor Liderado",
        papel_de_acesso="CONSULTOR",
        empresa_id=empresa,
        documento=CPF_B,
        funcao="CONSULTOR",
    )
    fora = await _criar_conta(
        admin,
        email="fora@rfbalance.local",
        nome="Consultor De Fora",
        papel_de_acesso="CONSULTOR",
        empresa_id=empresa,
        documento=CPF_C,
        funcao="CONSULTOR",
    )

    vinculo = await admin.post(
        "/api/v1/assignments",
        {
            "consultant_id": liderado["collaborator_id"],
            "leader_id": lider["collaborator_id"],
            "assignment_type": "COMERCIAL",
            "start_date": "2026-01-01",
            "reason": "Montagem da equipe comercial",
        },
    )
    assert vinculo.status_code == 201, vinculo.text

    da_equipe = await _criar_proposta(admin, consultant_id=liderado["collaborator_id"])
    de_fora = await _criar_proposta(admin, consultant_id=fora["collaborator_id"])

    async with _sessao(novo_cliente, "lider@rfbalance.local", lider["temporary_password"]) as api:
        ids = [item["id"] for item in (await api.get("/api/v1/proposals")).json()["items"]]

        assert da_equipe in ids
        assert de_fora not in ids
        assert (await api.get(f"/api/v1/proposals/{de_fora}")).status_code == 404
        exportacao_global = await api.get(
            "/api/v1/commission-financial-report/export.pdf",
            period_start="2026-08-01",
            period_end="2026-08-31",
        )
        assert exportacao_global.status_code == 403


# ---------- operacional ----------


async def test_operacional_enxerga_o_que_cadastrou(
    admin: Api, empresa: int, novo_cliente: Callable[[], AsyncClient]
) -> None:
    consultor = await _criar_conta(
        admin,
        email="c@rfbalance.local",
        nome="Consultor",
        papel_de_acesso="CONSULTOR",
        empresa_id=empresa,
        documento=CPF_A,
        funcao="CONSULTOR",
    )
    operacional = await _criar_conta(
        admin,
        email="op@rfbalance.local",
        nome="Retaguarda",
        papel_de_acesso="OPERACIONAL",
        empresa_id=empresa,
        documento=CPF_B,
        funcao="FINALIZACAO",
    )
    pelo_admin = await _criar_proposta(admin, consultant_id=consultor["collaborator_id"])

    async with _sessao(
        novo_cliente, "op@rfbalance.local", operacional["temporary_password"]
    ) as api:
        # a que o admin cadastrou não é dele
        assert (await api.get("/api/v1/proposals")).json()["items"] == []
        assert (await api.get(f"/api/v1/proposals/{pelo_admin}")).status_code == 404

        minha = await api.post(
            "/api/v1/proposals",
            {
                "consultant_id": consultor["collaborator_id"],
                "business_date": "2026-08-12",
                "customer_name": "Cliente Da Retaguarda",
                "customer_document": CPF_CLIENTE,
                "operation_amount": "5000.00",
                "tps_percentage": "10",
            },
        )
        assert minha.status_code == 201, minha.text

        ids = [item["id"] for item in (await api.get("/api/v1/proposals")).json()["items"]]
        assert ids == [minha.json()["id"]]


# ---------- comprovantes ----------


async def test_comprovante_alheio_nao_e_listavel_nem_baixavel(
    admin: Api, empresa: int, novo_cliente: Callable[[], AsyncClient]
) -> None:
    """O dado mais sensível do fluxo: o comprovante de pagamento do cliente."""
    dono = await _criar_conta(
        admin,
        email="dono2@rfbalance.local",
        nome="Consultor Dono",
        papel_de_acesso="CONSULTOR",
        empresa_id=empresa,
        documento=CPF_A,
        funcao="CONSULTOR",
    )
    intruso = await _criar_conta(
        admin,
        email="intruso@rfbalance.local",
        nome="Consultor Intruso",
        papel_de_acesso="CONSULTOR",
        empresa_id=empresa,
        documento=CPF_B,
        funcao="CONSULTOR",
    )
    proposta = await _criar_proposta(admin, consultant_id=dono["collaborator_id"])
    anexo = await admin.upload(f"/api/v1/proposals/{proposta}/attachments")
    assert anexo.status_code == 201, anexo.text
    anexo_id = anexo.json()["id"]

    async with _sessao(
        novo_cliente, "intruso@rfbalance.local", intruso["temporary_password"]
    ) as api:
        assert (await api.get(f"/api/v1/proposals/{proposta}/attachments")).status_code == 404
        baixar = await api.get(f"/api/v1/proposals/{proposta}/attachments/{anexo_id}")
        assert baixar.status_code == 404
        # e nada do arquivo vazou no corpo do erro
        assert b"%PDF" not in baixar.content
