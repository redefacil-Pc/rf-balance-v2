"""Cadastros e vínculos da F2, ponta a ponta (seções 7.2, 7.3, 16.3).

Cobre: cadastro de empresa/unidade/colaborador, deduplicação por documento,
mascaramento de PII por permissão, filtros de listagem, transferência de líder
com fechamento no dia anterior, proibição de sobreposição, e a consulta
histórica de líder na data.
"""

from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import text

from app.platform.config.security import CSRF_COOKIE, CSRF_HEADER
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine

pytestmark = pytest.mark.integration

CPF_CONSULTOR = "529.982.247-25"
CPF_LIDER = "111.444.777-35"
CPF_OUTRO = "390.533.447-05"
CNPJ_EMPRESA = "11.222.333/0001-81"


class Api:
    """Envolve o cliente já autenticado, com o header CSRF em toda mutação."""

    def __init__(self, cliente: AsyncClient) -> None:
        self._cliente = cliente

    @property
    def _csrf(self) -> dict[str, str]:
        return {CSRF_HEADER: self._cliente.cookies[CSRF_COOKIE]}

    async def post(self, caminho: str, corpo: dict[str, object]) -> Response:
        return await self._cliente.post(caminho, json=corpo, headers=self._csrf)

    async def get(self, caminho: str, **params: object) -> Response:
        return await self._cliente.get(caminho, params=params or None)


@pytest.fixture
async def api(cliente: AsyncClient, admin_semeado: dict[str, str]) -> Api:
    await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )
    return Api(cliente)


@pytest.fixture
async def empresa_e_unidade(api: Api) -> tuple[int, int]:
    empresa = await api.post(
        "/api/v1/companies",
        {"legal_name": "RF Balance LTDA", "trade_name": "RF Balance", "document": CNPJ_EMPRESA},
    )
    assert empresa.status_code == 201
    company_id = empresa.json()["id"]

    unidade = await api.post(
        "/api/v1/units", {"company_id": company_id, "code": "matriz", "name": "Matriz"}
    )
    assert unidade.status_code == 201
    return company_id, unidade.json()["id"]


async def _criar_colaborador(
    api: Api,
    *,
    company_id: int,
    unit_id: int | None,
    nome: str,
    documento: str,
    papel: str,
    desde: date = date(2026, 1, 1),
    pix: dict[str, str] | None = None,
) -> int:
    corpo: dict[str, object] = {
        "company_id": company_id,
        "unit_id": unit_id,
        "full_name": nome,
        "document": documento,
        "tax_regime": "MEI",
        "roles": [{"role": papel, "valid_from": desde.isoformat()}],
    }
    if pix:
        corpo["payment_key"] = pix

    resposta = await api.post("/api/v1/collaborators", corpo)
    assert resposta.status_code == 201, resposta.text
    return int(resposta.json()["id"])


# ---------- cadastro ----------


async def test_cadastra_colaborador_com_papel_e_pix(
    api: Api, empresa_e_unidade: tuple[int, int]
) -> None:
    company_id, unit_id = empresa_e_unidade

    resposta = await api.post(
        "/api/v1/collaborators",
        {
            "company_id": company_id,
            "unit_id": unit_id,
            "full_name": "Maria Consultora",
            "document": CPF_CONSULTOR,
            "tax_regime": "MEI",
            "roles": [{"role": "CONSULTOR", "valid_from": "2026-01-01"}],
            "payment_key": {"key_type": "CPF", "key": "52998224725"},
        },
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["roles"] == ["CONSULTOR"]
    # a criação nunca devolve documento completo
    assert corpo["document"] == "***.***.247-25"


async def test_documento_duplicado_e_rejeitado(
    api: Api, empresa_e_unidade: tuple[int, int]
) -> None:
    company_id, unit_id = empresa_e_unidade
    await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Maria Consultora",
        documento=CPF_CONSULTOR,
        papel="CONSULTOR",
    )

    repetido = await api.post(
        "/api/v1/collaborators",
        {
            "company_id": company_id,
            "unit_id": unit_id,
            "full_name": "Maria Com Outro Nome",
            # mesmo documento, formatação diferente: o hash normaliza antes
            "document": "52998224725",
            "tax_regime": "CLT",
            "roles": [{"role": "CONSULTOR", "valid_from": "2026-01-01"}],
        },
    )

    assert repetido.status_code == 409
    assert repetido.json()["type"].endswith("documento-duplicado")


async def test_documento_invalido_e_rejeitado(api: Api, empresa_e_unidade: tuple[int, int]) -> None:
    company_id, unit_id = empresa_e_unidade

    resposta = await api.post(
        "/api/v1/collaborators",
        {
            "company_id": company_id,
            "unit_id": unit_id,
            "full_name": "Documento Ruim",
            "document": "529.982.247-26",
            "tax_regime": "MEI",
            "roles": [{"role": "CONSULTOR", "valid_from": "2026-01-01"}],
        },
    )

    assert resposta.status_code == 422
    assert resposta.json()["type"].endswith("documento-invalido")


async def test_unidade_de_outra_empresa_e_rejeitada(api: Api) -> None:
    primeira = await api.post("/api/v1/companies", {"legal_name": "Empresa A"})
    segunda = await api.post("/api/v1/companies", {"legal_name": "Empresa B"})
    unidade_da_primeira = await api.post(
        "/api/v1/units", {"company_id": primeira.json()["id"], "code": "A1", "name": "Unidade A1"}
    )

    resposta = await api.post(
        "/api/v1/collaborators",
        {
            "company_id": segunda.json()["id"],
            "unit_id": unidade_da_primeira.json()["id"],
            "full_name": "Colaborador Trocado",
            "document": CPF_CONSULTOR,
            "tax_regime": "MEI",
            "roles": [{"role": "CONSULTOR", "valid_from": "2026-01-01"}],
        },
    )

    assert resposta.status_code == 422
    assert resposta.json()["type"].endswith("unidade-de-outra-empresa")


# ---------- listagem e PII ----------


async def test_listagem_mascara_documento_sem_permissao_de_pii(
    api: Api, empresa_e_unidade: tuple[int, int], cliente: AsyncClient
) -> None:
    company_id, unit_id = empresa_e_unidade
    await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Maria Consultora",
        documento=CPF_CONSULTOR,
        papel="CONSULTOR",
    )

    # o admin semeado tem read_pii: vê o documento completo
    resposta = await api.get("/api/v1/collaborators")
    assert resposta.status_code == 200
    assert resposta.json()["items"][0]["document"] == "529.982.247-25"


async def test_sem_permissao_de_pii_o_documento_vem_mascarado(
    api: Api,
    empresa_e_unidade: tuple[int, int],
    cliente: AsyncClient,
    admin_semeado: dict[str, str],
) -> None:
    """Quem cadastra não precisa ver o documento inteiro (ADR-0012).

    A permissão é retirada do papel para exercitar o caminho de mascaramento —
    é o que acontece na prática com o perfil Operação.
    """
    company_id, unit_id = empresa_e_unidade
    await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Maria Consultora",
        documento=CPF_CONSULTOR,
        papel="CONSULTOR",
    )

    engine = criar_engine(get_settings().database)
    try:
        async with engine.begin() as conexao:
            await conexao.execute(
                text(
                    "DELETE rp FROM role_permissions rp "
                    "JOIN permissions p ON p.id = rp.permission_id "
                    "WHERE p.code = 'collaborators:read_pii'"
                )
            )
    finally:
        await engine.dispose()

    # sessão nova para não reaproveitar o cache de permissões
    await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )

    resposta = await api.get("/api/v1/collaborators")

    assert resposta.status_code == 200
    documento = resposta.json()["items"][0]["document"]
    assert documento == "***.***.247-25"
    assert "529" not in documento


async def test_filtra_por_papel_vigente(api: Api, empresa_e_unidade: tuple[int, int]) -> None:
    company_id, unit_id = empresa_e_unidade
    await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Ana Consultora",
        documento=CPF_CONSULTOR,
        papel="CONSULTOR",
    )
    await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Bruno Lider",
        documento=CPF_LIDER,
        papel="LIDER",
    )

    somente_lideres = await api.get("/api/v1/collaborators", role="LIDER")

    nomes = [item["full_name"] for item in somente_lideres.json()["items"]]
    assert nomes == ["Bruno Lider"]


async def test_paginacao_por_cursor_nao_repete_nem_perde_registro(
    api: Api, empresa_e_unidade: tuple[int, int]
) -> None:
    company_id, unit_id = empresa_e_unidade
    for nome, documento in (
        ("Ana", CPF_CONSULTOR),
        ("Bruno", CPF_LIDER),
        ("Carla", CPF_OUTRO),
    ):
        await _criar_colaborador(
            api,
            company_id=company_id,
            unit_id=unit_id,
            nome=nome,
            documento=documento,
            papel="CONSULTOR",
        )

    primeira = (await api.get("/api/v1/collaborators", limit=2)).json()
    assert [item["full_name"] for item in primeira["items"]] == ["Ana", "Bruno"]
    assert primeira["next_cursor"]

    segunda = (
        await api.get("/api/v1/collaborators", limit=2, cursor=primeira["next_cursor"])
    ).json()
    assert [item["full_name"] for item in segunda["items"]] == ["Carla"]
    assert segunda["next_cursor"] is None


# ---------- vínculos ----------


async def test_transferencia_fecha_vinculo_anterior_no_dia_anterior(
    api: Api, empresa_e_unidade: tuple[int, int]
) -> None:
    company_id, unit_id = empresa_e_unidade
    consultor = await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Ana Consultora",
        documento=CPF_CONSULTOR,
        papel="CONSULTOR",
    )
    primeiro_lider = await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Bruno Lider",
        documento=CPF_LIDER,
        papel="LIDER",
    )
    segundo_lider = await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Carla Lider",
        documento=CPF_OUTRO,
        papel="LIDER",
    )

    await api.post(
        "/api/v1/assignments",
        {
            "consultant_id": consultor,
            "leader_id": primeiro_lider,
            "assignment_type": "COMERCIAL",
            "start_date": "2026-02-01",
            "reason": "vínculo inicial",
        },
    )
    transferencia = await api.post(
        "/api/v1/assignments",
        {
            "consultant_id": consultor,
            "leader_id": segundo_lider,
            "assignment_type": "COMERCIAL",
            "start_date": "2026-08-15",
            "reason": "mudança de equipe",
        },
    )

    assert transferencia.status_code == 201
    assert transferencia.json()["previous_closed_on"] == "2026-08-14"

    historico = (await api.get(f"/api/v1/assignments/consultant/{consultor}")).json()
    assert [(v["start_date"], v["end_date"]) for v in historico] == [
        ("2026-02-01", "2026-08-14"),
        ("2026-08-15", None),
    ]


async def test_lider_na_data_respeita_a_fronteira_do_intervalo(
    api: Api, empresa_e_unidade: tuple[int, int]
) -> None:
    """O caso obrigatório 16.2: vínculo que muda na fronteira de data."""
    company_id, unit_id = empresa_e_unidade
    consultor = await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Ana Consultora",
        documento=CPF_CONSULTOR,
        papel="CONSULTOR",
    )
    primeiro = await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Bruno Lider",
        documento=CPF_LIDER,
        papel="LIDER",
    )
    segundo = await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Carla Lider",
        documento=CPF_OUTRO,
        papel="LIDER",
    )

    await api.post(
        "/api/v1/assignments",
        {
            "consultant_id": consultor,
            "leader_id": primeiro,
            "assignment_type": "COMERCIAL",
            "start_date": "2026-02-01",
            "reason": "inicial",
        },
    )
    await api.post(
        "/api/v1/assignments",
        {
            "consultant_id": consultor,
            "leader_id": segundo,
            "assignment_type": "COMERCIAL",
            "start_date": "2026-08-15",
            "reason": "transferência",
        },
    )

    async def lider_em(dia: str) -> int | None:
        resposta = await api.get(
            "/api/v1/assignments/leader", consultant_id=consultor, reference_date=dia
        )
        corpo = resposta.json()
        return corpo["leader_id"] if corpo else None

    assert await lider_em("2026-08-14") == primeiro
    assert await lider_em("2026-08-15") == segundo
    # antes do primeiro vínculo não há líder
    assert await lider_em("2026-01-31") is None


async def test_vinculo_sobreposto_e_rejeitado(api: Api, empresa_e_unidade: tuple[int, int]) -> None:
    company_id, unit_id = empresa_e_unidade
    consultor = await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Ana Consultora",
        documento=CPF_CONSULTOR,
        papel="CONSULTOR",
    )
    lider = await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Bruno Lider",
        documento=CPF_LIDER,
        papel="LIDER",
    )

    await api.post(
        "/api/v1/assignments",
        {
            "consultant_id": consultor,
            "leader_id": lider,
            "assignment_type": "COMERCIAL",
            "start_date": "2026-02-01",
            "reason": "inicial",
        },
    )
    repetido = await api.post(
        "/api/v1/assignments",
        {
            "consultant_id": consultor,
            "leader_id": lider,
            "assignment_type": "COMERCIAL",
            "start_date": "2026-03-01",
            "reason": "duplicado",
        },
    )

    assert repetido.status_code == 409
    assert repetido.json()["type"].endswith("vigencia-sobreposta")


async def test_papel_incompativel_e_rejeitado(api: Api, empresa_e_unidade: tuple[int, int]) -> None:
    """Um BKO não pode liderar vínculo comercial (invariante da seção 7.3)."""
    company_id, unit_id = empresa_e_unidade
    consultor = await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Ana Consultora",
        documento=CPF_CONSULTOR,
        papel="CONSULTOR",
    )
    bko = await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Bruno BKO",
        documento=CPF_LIDER,
        papel="BKO",
    )

    resposta = await api.post(
        "/api/v1/assignments",
        {
            "consultant_id": consultor,
            "leader_id": bko,
            "assignment_type": "COMERCIAL",
            "start_date": "2026-02-01",
            "reason": "tentativa inválida",
        },
    )

    assert resposta.status_code == 422
    assert resposta.json()["type"].endswith("papel-incompativel")


async def test_inativacao_encerra_vinculos_e_bloqueia_novos(
    api: Api, empresa_e_unidade: tuple[int, int]
) -> None:
    company_id, unit_id = empresa_e_unidade
    consultor = await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Ana Consultora",
        documento=CPF_CONSULTOR,
        papel="CONSULTOR",
    )
    lider = await _criar_colaborador(
        api,
        company_id=company_id,
        unit_id=unit_id,
        nome="Bruno Lider",
        documento=CPF_LIDER,
        papel="LIDER",
    )
    await api.post(
        "/api/v1/assignments",
        {
            "consultant_id": consultor,
            "leader_id": lider,
            "assignment_type": "COMERCIAL",
            "start_date": "2026-02-01",
            "reason": "inicial",
        },
    )

    inativacao = await api.post(
        f"/api/v1/collaborators/{consultor}/deactivation",
        {"deactivated_on": "2026-08-31", "reason": "desligamento"},
    )

    assert inativacao.status_code == 200
    assert inativacao.json()["closed_assignments"] == 1

    novo_vinculo = await api.post(
        "/api/v1/assignments",
        {
            "consultant_id": consultor,
            "leader_id": lider,
            "assignment_type": "COMERCIAL",
            "start_date": "2026-09-01",
            "reason": "não deveria passar",
        },
    )
    assert novo_vinculo.status_code == 409
    assert novo_vinculo.json()["type"].endswith("colaborador-inativo")


# ---------- autorização ----------


async def test_rotas_de_cadastro_exigem_sessao(cliente: AsyncClient) -> None:
    sem_sessao = await cliente.get("/api/v1/collaborators")

    assert sem_sessao.status_code == 401


async def test_mutacao_sem_csrf_e_recusada(
    cliente: AsyncClient, admin_semeado: dict[str, str]
) -> None:
    await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )

    resposta = await cliente.post("/api/v1/companies", json={"legal_name": "Sem CSRF"})

    assert resposta.status_code == 403
