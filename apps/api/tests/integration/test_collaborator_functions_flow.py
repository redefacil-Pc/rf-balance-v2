"""Gestão de funções operacionais do colaborador (ADR-0013).

A regra que dá sentido a tudo aqui: trocar de função é **encerrar uma linha e
abrir outra**, nunca sobrescrever. É isso que permite comissionar uma proposta
de março pela função que a pessoa tinha em março.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient, Response

from app.platform.config.security import CSRF_COOKIE, CSRF_HEADER

pytestmark = pytest.mark.integration

CPF = "529.982.247-25"
CNPJ_EMPRESA = "04.252.011/0001-10"


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

    async def get(self, caminho: str) -> Response:
        return await self._cliente.get(caminho)


@pytest.fixture
async def api(cliente: AsyncClient, admin_semeado: dict[str, str]) -> Api:
    await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )
    return Api(cliente)


@pytest.fixture
async def colaborador(api: Api) -> int:
    empresa = await api.post(
        "/api/v1/companies",
        {"legal_name": "RF Balance LTDA", "trade_name": "RF Balance", "document": CNPJ_EMPRESA},
    )
    assert empresa.status_code == 201, empresa.text

    criado = await api.post(
        "/api/v1/collaborators",
        {
            "company_id": empresa.json()["id"],
            "unit_id": None,
            "full_name": "Pessoa Polivalente",
            "document": CPF,
            "tax_regime": "CLT",
            "roles": [{"role": "BKO", "valid_from": "2026-01-01"}],
        },
    )
    assert criado.status_code == 201, criado.text
    return int(criado.json()["id"])


async def _funcoes(api: Api, colaborador: int) -> list[dict[str, Any]]:
    resposta = await api.get(f"/api/v1/collaborators/{colaborador}/functions")
    assert resposta.status_code == 200, resposta.text
    corpo: list[dict[str, Any]] = resposta.json()
    return corpo


# ---------- vínculo com conta na criação ----------


async def test_criacao_vincula_conta_no_mesmo_commit(api: Api) -> None:
    """Cadastro em dois passos deixaria a pessoa sem acesso se o segundo
    falhasse; aqui colaborador e vínculo nascem juntos."""
    empresa = await api.post(
        "/api/v1/companies",
        {"legal_name": "Outra LTDA", "trade_name": "Outra", "document": "11.222.333/0001-81"},
    )
    conta = await api.post(
        "/api/v1/users",
        {"email": "livre@rfbalance.local", "full_name": "Conta Livre", "roles": ["CONSULTOR"]},
    )
    assert conta.status_code == 201, conta.text

    criado = await api.post(
        "/api/v1/collaborators",
        {
            "company_id": empresa.json()["id"],
            "unit_id": None,
            "full_name": "Conta Livre",
            "document": "390.533.447-05",
            "tax_regime": "MEI",
            "roles": [{"role": "CONSULTOR", "valid_from": "2026-01-01"}],
            "user_id": conta.json()["id"],
        },
    )
    assert criado.status_code == 201, criado.text

    detalhe = await api.get(f"/api/v1/users/{conta.json()['id']}")
    assert detalhe.json()["collaborator_id"] == criado.json()["id"]


async def test_conta_ja_vinculada_e_recusada(api: Api, colaborador: int) -> None:
    conta = await api.post(
        "/api/v1/users",
        {"email": "dupla@rfbalance.local", "full_name": "Conta Dupla", "roles": ["CONSULTOR"]},
    )
    vinculo = await api.put(
        f"/api/v1/collaborators/{colaborador}/account", {"user_id": conta.json()["id"]}
    )
    assert vinculo.status_code == 204, vinculo.text

    empresa = await api.get("/api/v1/companies")
    repetido = await api.post(
        "/api/v1/collaborators",
        {
            "company_id": empresa.json()[0]["id"],
            "unit_id": None,
            "full_name": "Outra Pessoa",
            "document": "390.533.447-05",
            "tax_regime": "MEI",
            "roles": [{"role": "CONSULTOR", "valid_from": "2026-01-01"}],
            "user_id": conta.json()["id"],
        },
    )

    assert repetido.status_code == 409
    assert repetido.json()["type"].endswith("conta-ja-vinculada")


# ---------- leitura ----------


async def test_funcao_do_cadastro_aparece_como_vigente(api: Api, colaborador: int) -> None:
    funcoes = await _funcoes(api, colaborador)

    assert len(funcoes) == 1
    assert funcoes[0]["role"] == "BKO"
    assert funcoes[0]["current"] is True
    assert funcoes[0]["valid_to"] is None


async def test_colaborador_inexistente_devolve_404(api: Api) -> None:
    assert (await api.get("/api/v1/collaborators/999999/functions")).status_code == 404


# ---------- acumular ----------


async def test_funcoes_diferentes_convivem(api: Api, colaborador: int) -> None:
    """Acumular função é o modelo (ADR-0013), não exceção."""
    aberta = await api.post(
        f"/api/v1/collaborators/{colaborador}/functions",
        {"function": "FINALIZACAO", "valid_from": "2026-03-01"},
    )
    assert aberta.status_code == 201, aberta.text

    vigentes = [f["role"] for f in await _funcoes(api, colaborador) if f["current"]]
    assert sorted(vigentes) == ["BKO", "FINALIZACAO"]


async def test_mesma_funcao_sobreposta_e_recusada(api: Api, colaborador: int) -> None:
    repetida = await api.post(
        f"/api/v1/collaborators/{colaborador}/functions",
        {"function": "BKO", "valid_from": "2026-06-01"},
    )

    assert repetida.status_code == 409
    assert repetida.json()["type"].endswith("vigencia-sobreposta")


async def test_mesma_funcao_em_periodo_livre_e_aceita(api: Api, colaborador: int) -> None:
    """Sem sobreposição não há conflito: a pessoa foi BKO, saiu, e voltou."""
    encerrada = await api.put(
        f"/api/v1/collaborators/{colaborador}/functions/"
        f"{(await _funcoes(api, colaborador))[0]['id']}/closure",
        {"valid_to": "2026-02-28"},
    )
    assert encerrada.status_code == 200, encerrada.text

    de_volta = await api.post(
        f"/api/v1/collaborators/{colaborador}/functions",
        {"function": "BKO", "valid_from": "2026-06-01"},
    )
    assert de_volta.status_code == 201, de_volta.text


# ---------- trocar de função ----------


async def test_troca_de_funcao_preserva_a_anterior(api: Api, colaborador: int) -> None:
    """O ponto central: a função antiga não some, ela é encerrada. Sem isso, uma
    proposta de janeiro seria comissionada pela função de março."""
    antiga = (await _funcoes(api, colaborador))[0]

    await api.put(
        f"/api/v1/collaborators/{colaborador}/functions/{antiga['id']}/closure",
        {"valid_to": "2026-02-28"},
    )
    await api.post(
        f"/api/v1/collaborators/{colaborador}/functions",
        {"function": "FINALIZACAO", "valid_from": "2026-03-01"},
    )

    funcoes = await _funcoes(api, colaborador)
    por_papel = {f["role"]: f for f in funcoes}

    assert len(funcoes) == 2
    # a história de janeiro continua contando a verdade
    assert por_papel["BKO"]["valid_to"] == "2026-02-28"
    assert por_papel["BKO"]["current"] is False
    assert por_papel["FINALIZACAO"]["current"] is True


async def test_troca_atomica_de_mei_para_mei_2_preserva_conta_e_historico(api: Api) -> None:
    hoje = date.today()
    empresa = await api.post(
        "/api/v1/companies",
        {"legal_name": "Modalidades LTDA", "trade_name": "Modalidades", "document": CNPJ_EMPRESA},
    )
    conta = await api.post(
        "/api/v1/users",
        {
            "email": "modalidade@rfbalance.local",
            "full_name": "Consultora Modalidade",
            "roles": ["CONSULTOR"],
        },
    )
    criado = await api.post(
        "/api/v1/collaborators",
        {
            "company_id": empresa.json()["id"],
            "unit_id": None,
            "full_name": "Consultora Modalidade",
            "document": CPF,
            "tax_regime": "MEI",
            "roles": [{"role": "CONSULTOR", "valid_from": "2026-01-01"}],
            "user_id": conta.json()["id"],
        },
    )
    assert criado.status_code == 201, criado.text

    alterado = await api.put(
        f"/api/v1/collaborators/{criado.json()['id']}",
        {
            "company_id": empresa.json()["id"],
            "unit_id": None,
            "full_name": "Consultora Modalidade",
            "tax_regime": "CLT",
            "email": "modalidade@rfbalance.local",
            "phone": None,
            "consultant_modality": "CONSULTOR_MEI_ESCALONADO",
            "modality_valid_from": hoje.isoformat(),
            "modality_reason": "mudança para cálculo escalonado",
        },
    )
    assert alterado.status_code == 204, alterado.text

    funcoes = await _funcoes(api, criado.json()["id"])
    por_papel = {item["role"]: item for item in funcoes}
    assert por_papel["CONSULTOR"]["valid_to"] == (hoje - timedelta(days=1)).isoformat()
    assert por_papel["CONSULTOR_MEI_ESCALONADO"]["valid_from"] == hoje.isoformat()
    assert por_papel["CONSULTOR_MEI_ESCALONADO"]["current"] is True

    cadastro = await api.get("/api/v1/collaborators?name=Consultora%20Modalidade")
    assert cadastro.json()["items"][0]["tax_regime"] == "CLT"

    detalhe_da_conta = await api.get(f"/api/v1/users/{conta.json()['id']}")
    assert detalhe_da_conta.json()["collaborator_id"] == criado.json()["id"]


async def test_modalidades_de_consultor_nao_podem_ser_acumuladas(
    api: Api, colaborador: int
) -> None:
    aberta = await api.post(
        f"/api/v1/collaborators/{colaborador}/functions",
        {"function": "CONSULTOR", "valid_from": "2026-01-01"},
    )
    assert aberta.status_code == 201, aberta.text

    segunda = await api.post(
        f"/api/v1/collaborators/{colaborador}/functions",
        {"function": "CONSULTOR_MEI_ESCALONADO", "valid_from": "2026-08-17"},
    )
    assert segunda.status_code == 409
    assert segunda.json()["type"].endswith("vigencia-sobreposta")


async def test_vigente_vem_antes_do_historico(api: Api, colaborador: int) -> None:
    antiga = (await _funcoes(api, colaborador))[0]
    await api.put(
        f"/api/v1/collaborators/{colaborador}/functions/{antiga['id']}/closure",
        {"valid_to": "2026-02-28"},
    )
    await api.post(
        f"/api/v1/collaborators/{colaborador}/functions",
        {"function": "CONSULTOR", "valid_from": "2026-03-01"},
    )

    funcoes = await _funcoes(api, colaborador)
    assert funcoes[0]["current"] is True
    assert funcoes[-1]["current"] is False


# ---------- encerramento ----------


async def test_encerramento_antes_do_inicio_e_recusado(api: Api, colaborador: int) -> None:
    alvo = (await _funcoes(api, colaborador))[0]

    invalido = await api.put(
        f"/api/v1/collaborators/{colaborador}/functions/{alvo['id']}/closure",
        {"valid_to": "2025-12-31"},
    )

    assert invalido.status_code == 409
    assert invalido.json()["type"].endswith("vigencia-sobreposta")


async def test_encerrar_duas_vezes_e_recusado(api: Api, colaborador: int) -> None:
    alvo = (await _funcoes(api, colaborador))[0]
    caminho = f"/api/v1/collaborators/{colaborador}/functions/{alvo['id']}/closure"

    assert (await api.put(caminho, {"valid_to": "2026-02-28"})).status_code == 200
    segunda = await api.put(caminho, {"valid_to": "2026-03-31"})

    assert segunda.status_code == 409


async def test_funcao_de_outro_colaborador_nao_e_encerravel(api: Api, colaborador: int) -> None:
    """O escopo pelo colaborador impede encerrar função alheia trocando o id."""
    alvo = (await _funcoes(api, colaborador))[0]

    resposta = await api.put(
        f"/api/v1/collaborators/999999/functions/{alvo['id']}/closure",
        {"valid_to": "2026-02-28"},
    )

    assert resposta.status_code == 404


# ---------- auditoria ----------


async def test_abertura_e_encerramento_geram_trilha(api: Api, colaborador: int) -> None:
    alvo = (await _funcoes(api, colaborador))[0]
    await api.put(
        f"/api/v1/collaborators/{colaborador}/functions/{alvo['id']}/closure",
        {"valid_to": "2026-02-28"},
    )
    await api.post(
        f"/api/v1/collaborators/{colaborador}/functions",
        {"function": "FINALIZACAO", "valid_from": "2026-03-01"},
    )

    acoes = await _acoes_de_auditoria(str(colaborador))
    assert "collaborator.function_closed" in acoes
    assert "collaborator.function_opened" in acoes


async def _acoes_de_auditoria(aggregate_id: str) -> list[str]:
    from sqlalchemy import text

    from app.platform.config.settings import get_settings
    from app.platform.db.engine import criar_engine

    engine = criar_engine(get_settings().database)
    try:
        async with engine.connect() as conexao:
            linhas = await conexao.execute(
                text(
                    "SELECT action FROM audit_events "
                    "WHERE aggregate_type = 'collaborator' AND aggregate_id = :id "
                    "ORDER BY id"
                ),
                {"id": aggregate_id},
            )
            return [str(linha[0]) for linha in linhas]
    finally:
        await engine.dispose()
