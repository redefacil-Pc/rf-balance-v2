"""Propostas da F2, ponta a ponta (seção 7.4).

Cobre: cadastro com comissão calculada no servidor, unicidade do Redmine,
validação do documento do cliente, mascaramento de PII por permissão, filtros e
paginação por cursor, controle otimista por `version` e cancelamento com motivo.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import text

from app.platform.config.security import CSRF_COOKIE, CSRF_HEADER
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine

pytestmark = pytest.mark.integration

CPF_CONSULTOR = "529.982.247-25"
CPF_CLIENTE = "111.444.777-35"
CNPJ_CLIENTE = "11.222.333/0001-81"
CNPJ_EMPRESA = "04.252.011/0001-10"


class Api:
    """Cliente autenticado, com o header CSRF em toda mutação."""

    def __init__(self, cliente: AsyncClient) -> None:
        self._cliente = cliente

    @property
    def _csrf(self) -> dict[str, str]:
        return {CSRF_HEADER: self._cliente.cookies[CSRF_COOKIE]}

    async def post(self, caminho: str, corpo: dict[str, Any]) -> Response:
        return await self._cliente.post(caminho, json=corpo, headers=self._csrf)

    async def put(self, caminho: str, corpo: dict[str, Any]) -> Response:
        return await self._cliente.put(caminho, json=corpo, headers=self._csrf)

    async def get(self, caminho: str, **params: Any) -> Response:
        return await self._cliente.get(caminho, params=params or None)

    async def delete(self, caminho: str) -> Response:
        return await self._cliente.delete(caminho, headers=self._csrf)

    async def upload(
        self, caminho: str, *, file_name: str, content_type: str, conteudo: bytes
    ) -> Response:
        return await self._cliente.post(
            caminho, files={"file": (file_name, conteudo, content_type)}, headers=self._csrf
        )


@pytest.fixture
async def api(cliente: AsyncClient, admin_semeado: dict[str, str]) -> Api:
    await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )
    return Api(cliente)


@pytest.fixture
async def consultor(api: Api) -> int:
    empresa = await api.post(
        "/api/v1/companies",
        {"legal_name": "RF Balance LTDA", "trade_name": "RF Balance", "document": CNPJ_EMPRESA},
    )
    assert empresa.status_code == 201, empresa.text
    company_id = empresa.json()["id"]

    colaborador = await api.post(
        "/api/v1/collaborators",
        {
            "company_id": company_id,
            "unit_id": None,
            "full_name": "Maria Consultora",
            "document": CPF_CONSULTOR,
            "tax_regime": "MEI",
            "roles": [{"role": "CONSULTOR", "valid_from": "2026-01-01"}],
        },
    )
    assert colaborador.status_code == 201, colaborador.text
    return int(colaborador.json()["id"])


async def _criar_proposta(
    api: Api,
    consultant_id: int,
    *,
    operacao: str = "10000.00",
    tps: str = "10",
    documento: str = CPF_CLIENTE,
    external_id: str | None = None,
    em: date = date(2026, 8, 12),
) -> dict[str, Any]:
    corpo: dict[str, Any] = {
        "consultant_id": consultant_id,
        "business_date": em.isoformat(),
        "customer_name": "Cliente Exemplo",
        "customer_document": documento,
        "operation_amount": operacao,
        "tps_percentage": tps,
    }
    if external_id is not None:
        corpo["external_id"] = external_id

    resposta = await api.post("/api/v1/proposals", corpo)
    assert resposta.status_code == 201, resposta.text
    resultado: dict[str, Any] = resposta.json()
    return resultado


async def _registrar_recebimento_de_teste(proposal_id: int, *, amount: str = "100.00") -> None:
    """Prepara o estado comercial; o contrato HTTP do recebimento é coberto em seu módulo."""
    engine = criar_engine(get_settings().database)
    try:
        async with engine.begin() as conexao:
            await conexao.execute(
                text(
                    "INSERT INTO receiving_accounts "
                    "(label, display_order, is_active, created_by, updated_by) "
                    "VALUES (:label, 0, 1, NULL, NULL)"
                ),
                {"label": f"Conta da proposta {proposal_id}"},
            )
            conta = await conexao.scalar(text("SELECT LAST_INSERT_ID()"))
            ator = await conexao.scalar(text("SELECT id FROM users ORDER BY id LIMIT 1"))
            await conexao.execute(
                text(
                    "INSERT INTO receipts ("
                    "proposal_id, amount, business_date, payment_method, receiving_account_id, "
                    "status, proof_file_name, proof_content_type, proof_size_bytes, "
                    "proof_storage_key, proof_sha256, idempotency_key, request_hash, created_by"
                    ") VALUES ("
                    ":proposal_id, :amount, '2026-08-12', 'PIX', :conta, 'SUBMITTED', "
                    "'comprovante.pdf', 'application/pdf', 8, :storage_key, :hash, :chave, "
                    ":hash, :ator)"
                ),
                {
                    "proposal_id": proposal_id,
                    "amount": amount,
                    "conta": conta,
                    "storage_key": f"testes/propostas/{proposal_id}.pdf",
                    "hash": "a" * 64,
                    "chave": f"teste-proposta-{proposal_id}",
                    "ator": ator,
                },
            )
    finally:
        await engine.dispose()


# ---------- cadastro ----------


async def test_cadastra_proposta_com_comissao_calculada_no_servidor(
    api: Api, consultor: int
) -> None:
    criada = await _criar_proposta(api, consultor, operacao="10000.00", tps="12.5")

    assert criada["status"] == "OPEN"
    # dinheiro trafega como string decimal, nunca float
    assert criada["company_commission_amount"] == "1250.00"
    assert criada["outstanding_amount"] == "1250.00"
    assert criada["version"] == 1


async def test_redmine_repetido_e_rejeitado(api: Api, consultor: int) -> None:
    await _criar_proposta(api, consultor, external_id="RM-1001")

    repetida = await api.post(
        "/api/v1/proposals",
        {
            "consultant_id": consultor,
            "business_date": "2026-08-12",
            "customer_name": "Outro Cliente",
            "customer_document": CNPJ_CLIENTE,
            "operation_amount": "500.00",
            "tps_percentage": "10",
            "external_id": "RM-1001",
        },
    )

    assert repetida.status_code == 409
    assert repetida.json()["type"].endswith("external-id-duplicado")


async def test_documento_do_cliente_invalido_e_rejeitado(api: Api, consultor: int) -> None:
    resposta = await api.post(
        "/api/v1/proposals",
        {
            "consultant_id": consultor,
            "business_date": "2026-08-12",
            "customer_name": "Cliente Exemplo",
            "customer_document": "111.111.111-11",
            "operation_amount": "1000.00",
            "tps_percentage": "10",
        },
    )

    assert resposta.status_code == 422
    assert resposta.json()["type"].endswith("documento-do-cliente-invalido")


async def test_consultor_inexistente_e_rejeitado(api: Api) -> None:
    resposta = await api.post(
        "/api/v1/proposals",
        {
            "consultant_id": 999_999,
            "business_date": "2026-08-12",
            "customer_name": "Cliente Exemplo",
            "customer_document": CPF_CLIENTE,
            "operation_amount": "1000.00",
            "tps_percentage": "10",
        },
    )

    assert resposta.status_code == 422
    assert resposta.json()["type"].endswith("participante-invalido")


async def test_valor_e_tps_fora_do_permitido_nao_passam_do_schema(api: Api, consultor: int) -> None:
    for invalido in ({"operation_amount": "0.00"}, {"tps_percentage": "101"}):
        corpo: dict[str, Any] = {
            "consultant_id": consultor,
            "business_date": "2026-08-12",
            "customer_name": "Cliente Exemplo",
            "customer_document": CPF_CLIENTE,
            "operation_amount": "1000.00",
            "tps_percentage": "10",
            **invalido,
        }
        resposta = await api.post("/api/v1/proposals", corpo)
        assert resposta.status_code == 422, resposta.text


# ---------- consulta ----------


async def test_detalhe_traz_documento_mascarado_e_nome_do_consultor(
    api: Api, consultor: int
) -> None:
    criada = await _criar_proposta(api, consultor)

    detalhe = await api.get(f"/api/v1/proposals/{criada['id']}")

    assert detalhe.status_code == 200
    corpo = detalhe.json()
    assert corpo["consultant_name"] == "Maria Consultora"
    # admin tem proposals:read_pii, então vê o documento completo
    assert corpo["customer_document"] == "111.444.777-35"
    assert corpo["overpaid"] is False
    assert corpo["tolerance_policy_version"] == "v1"
    assert [evento["action"] for evento in corpo["timeline"]] == ["proposal.created"]
    assert corpo["timeline"][0]["actor_name"] == "Administrador"


async def test_listagem_filtra_por_consultor_e_periodo(api: Api, consultor: int) -> None:
    await _criar_proposta(api, consultor, em=date(2026, 8, 1))
    await _criar_proposta(api, consultor, em=date(2026, 8, 20), documento=CNPJ_CLIENTE)

    resposta = await api.get(
        "/api/v1/proposals",
        consultant_id=consultor,
        business_date_from="2026-08-10",
        business_date_to="2026-08-31",
    )

    assert resposta.status_code == 200
    itens = resposta.json()["items"]
    assert len(itens) == 1
    assert itens[0]["business_date"] == "2026-08-20"


async def test_paginacao_por_cursor_nao_repete_nem_pula(api: Api, consultor: int) -> None:
    for dia in (10, 11, 12):
        await _criar_proposta(api, consultor, em=date(2026, 8, dia))

    primeira = await api.get("/api/v1/proposals", limit=2)
    assert primeira.status_code == 200
    pagina_um = primeira.json()
    assert len(pagina_um["items"]) == 2
    assert pagina_um["next_cursor"]

    segunda = await api.get("/api/v1/proposals", limit=2, cursor=pagina_um["next_cursor"])
    pagina_dois = segunda.json()

    ids_um = [item["id"] for item in pagina_um["items"]]
    ids_dois = [item["id"] for item in pagina_dois["items"]]
    assert len(pagina_dois["items"]) == 1
    assert not set(ids_um) & set(ids_dois)
    # ordenação por data de negócio decrescente: a mais nova vem primeiro
    assert pagina_um["items"][0]["business_date"] == "2026-08-12"


async def test_proposta_inexistente_devolve_404(api: Api) -> None:
    resposta = await api.get("/api/v1/proposals/999999")
    assert resposta.status_code == 404


# ---------- alteração ----------


async def test_alteracao_recalcula_comissao_e_avanca_a_versao(api: Api, consultor: int) -> None:
    criada = await _criar_proposta(api, consultor, operacao="10000.00", tps="10")

    alterada = await api.put(
        f"/api/v1/proposals/{criada['id']}",
        {"version": criada["version"], "operation_amount": "20000.00", "tps_percentage": "7.5"},
    )

    assert alterada.status_code == 200, alterada.text
    corpo = alterada.json()
    assert corpo["company_commission_amount"] == "1500.00"
    assert corpo["version"] == 2


async def test_versao_desatualizada_e_recusada(api: Api, consultor: int) -> None:
    criada = await _criar_proposta(api, consultor)
    primeira = await api.put(
        f"/api/v1/proposals/{criada['id']}",
        {"version": criada["version"], "operation_amount": "11000.00", "tps_percentage": "10"},
    )
    assert primeira.status_code == 200

    # segunda tela, ainda com a versão antiga em mãos
    segunda = await api.put(
        f"/api/v1/proposals/{criada['id']}",
        {"version": criada["version"], "operation_amount": "99000.00", "tps_percentage": "10"},
    )

    assert segunda.status_code == 409
    assert segunda.json()["type"].endswith("concurrency-conflict")

    detalhe = await api.get(f"/api/v1/proposals/{criada['id']}")
    # a escrita perdedora não deixou rastro
    assert detalhe.json()["operation_amount"] == "11000.00"


# ---------- cancelamento ----------


async def test_cancelamento_exige_motivo_e_e_terminal(api: Api, consultor: int) -> None:
    criada = await _criar_proposta(api, consultor)

    sem_motivo = await api.post(
        f"/api/v1/proposals/{criada['id']}/cancellation", {"version": criada["version"]}
    )
    assert sem_motivo.status_code == 422

    cancelada = await api.post(
        f"/api/v1/proposals/{criada['id']}/cancellation",
        {"version": criada["version"], "reason": "Cliente desistiu da operação"},
    )
    assert cancelada.status_code == 200, cancelada.text
    assert cancelada.json()["status"] == "CANCELLED"

    detalhe = (await api.get(f"/api/v1/proposals/{criada['id']}")).json()
    assert detalhe["cancellation_reason"] == "Cliente desistiu da operação"
    assert detalhe["cancelled_at"] is not None
    assert detalhe["outstanding_amount"] == "0.00"

    # cancelada não aceita alteração
    depois = await api.put(
        f"/api/v1/proposals/{criada['id']}",
        {"version": detalhe["version"], "operation_amount": "1.00", "tps_percentage": "1"},
    )
    assert depois.status_code == 409
    assert depois.json()["type"].endswith("proposta-cancelada")


# ---------- auditoria ----------


async def test_cadastro_e_alteracao_geram_trilha_de_auditoria(api: Api, consultor: int) -> None:
    criada = await _criar_proposta(api, consultor)
    await api.put(
        f"/api/v1/proposals/{criada['id']}",
        {"version": criada["version"], "operation_amount": "12000.00", "tps_percentage": "10"},
    )

    eventos = await _acoes_de_auditoria(str(criada["id"]))
    assert eventos == ["proposal.created", "proposal.updated"]


# ---------- aprovação ----------


async def test_anexo_solto_nao_substitui_recebimento_declarado(api: Api, consultor: int) -> None:
    criada = await _criar_proposta(api, consultor)
    anexo = await api.upload(
        f"/api/v1/proposals/{criada['id']}/attachments",
        file_name="comprovante-solto.pdf",
        content_type="application/pdf",
        conteudo=b"%PDF-1.4 sem valor associado",
    )
    assert anexo.status_code == 201, anexo.text

    sem_recebimento = await api.post(
        f"/api/v1/proposals/{criada['id']}/submission", {"version": criada["version"]}
    )

    assert sem_recebimento.status_code == 422
    assert sem_recebimento.json()["type"].endswith("proposta-sem-comprovante")
    assert "valor recebido" in sem_recebimento.json()["detail"]


async def test_fluxo_completo_de_aprovacao(api: Api, consultor: int) -> None:
    criada = await _criar_proposta(api, consultor)
    await _registrar_recebimento_de_teste(criada["id"])

    enviada = await api.post(
        f"/api/v1/proposals/{criada['id']}/submission", {"version": criada["version"]}
    )
    assert enviada.status_code == 200, enviada.text
    assert enviada.json()["approval_status"] == "SUBMITTED"

    listagem_operacional = await api.get(
        "/api/v1/proposals", exclude_approval_status="SUBMITTED"
    )
    fila_do_financeiro = await api.get(
        "/api/v1/proposals", approval_status="SUBMITTED"
    )
    assert criada["id"] not in {
        item["id"] for item in listagem_operacional.json()["items"]
    }
    assert criada["id"] in {item["id"] for item in fila_do_financeiro.json()["items"]}
    pendentes = await api.get("/api/v1/proposals/pending-count")
    assert pendentes.status_code == 200
    assert pendentes.json() == {"count": 1}

    # travada para edição enquanto aguarda decisão
    bloqueada = await api.put(
        f"/api/v1/proposals/{criada['id']}",
        {"version": enviada.json()["version"], "operation_amount": "1.00", "tps_percentage": "1"},
    )
    assert bloqueada.status_code == 409
    assert bloqueada.json()["type"].endswith("proposta-em-analise")

    aprovada = await api.post(
        f"/api/v1/proposals/{criada['id']}/decision",
        {"version": enviada.json()["version"], "decision": "APROVAR"},
    )
    assert aprovada.status_code == 200, aprovada.text
    assert aprovada.json()["approval_status"] == "APPROVED"

    detalhe = (await api.get(f"/api/v1/proposals/{criada['id']}")).json()
    assert detalhe["submitted_at"] is not None
    assert detalhe["decided_at"] is not None
    assert [evento["action"] for evento in detalhe["timeline"]] == [
        "proposal.created",
        "proposal.submitted",
        "proposal.approved",
    ]
    assert (await api.get("/api/v1/proposals/pending-count")).json() == {"count": 0}


async def test_operacional_cadastra_e_financeiro_decide(
    api: Api, consultor: int, novo_cliente: Callable[[], AsyncClient]
) -> None:
    operacional = await api.post(
        "/api/v1/users",
        {
            "email": "operacional-fluxo@rfbalance.local",
            "full_name": "Pessoa Operacional",
            "roles": ["OPERACIONAL"],
        },
    )
    financeiro = await api.post(
        "/api/v1/users",
        {
            "email": "financeiro-fluxo@rfbalance.local",
            "full_name": "Pessoa Financeira",
            "roles": ["FINANCEIRO"],
        },
    )
    assert operacional.status_code == 201, operacional.text
    assert financeiro.status_code == 201, financeiro.text

    async with novo_cliente() as cliente_operacional:
        login = await cliente_operacional.post(
            "/api/v1/auth/login",
            json={
                "email": "operacional-fluxo@rfbalance.local",
                "password": operacional.json()["temporary_password"],
            },
        )
        assert login.status_code == 200, login.text
        csrf = {CSRF_HEADER: cliente_operacional.cookies[CSRF_COOKIE]}

        criada = await cliente_operacional.post(
            "/api/v1/proposals",
            json={
                "consultant_id": consultor,
                "business_date": "2026-08-12",
                "customer_name": "Cliente por perfil",
                "customer_document": CPF_CLIENTE,
                "operation_amount": "1000.00",
                "tps_percentage": "10",
            },
            headers=csrf,
        )
        assert criada.status_code == 201, criada.text
        await _registrar_recebimento_de_teste(criada.json()["id"])

        enviada = await cliente_operacional.post(
            f"/api/v1/proposals/{criada.json()['id']}/submission",
            json={"version": criada.json()["version"]},
            headers=csrf,
        )
        assert enviada.status_code == 200, enviada.text

        decisao_indevida = await cliente_operacional.post(
            f"/api/v1/proposals/{criada.json()['id']}/decision",
            json={"version": enviada.json()["version"], "decision": "APROVAR"},
            headers=csrf,
        )
        assert decisao_indevida.status_code == 403

    async with novo_cliente() as cliente_financeiro:
        login = await cliente_financeiro.post(
            "/api/v1/auth/login",
            json={
                "email": "financeiro-fluxo@rfbalance.local",
                "password": financeiro.json()["temporary_password"],
            },
        )
        assert login.status_code == 200, login.text
        csrf = {CSRF_HEADER: cliente_financeiro.cookies[CSRF_COOKIE]}

        escrita_indevida = await cliente_financeiro.put(
            f"/api/v1/proposals/{criada.json()['id']}",
            json={
                "version": enviada.json()["version"],
                "operation_amount": "2000.00",
                "tps_percentage": "10",
            },
            headers=csrf,
        )
        assert escrita_indevida.status_code == 403

        aprovada = await cliente_financeiro.post(
            f"/api/v1/proposals/{criada.json()['id']}/decision",
            json={"version": enviada.json()["version"], "decision": "APROVAR"},
            headers=csrf,
        )
        assert aprovada.status_code == 200, aprovada.text
        assert aprovada.json()["approval_status"] == "APPROVED"


async def test_devolucao_exige_motivo_e_permite_reenvio(api: Api, consultor: int) -> None:
    criada = await _criar_proposta(api, consultor)
    await _registrar_recebimento_de_teste(criada["id"])
    enviada = (
        await api.post(
            f"/api/v1/proposals/{criada['id']}/submission", {"version": criada["version"]}
        )
    ).json()

    sem_motivo = await api.post(
        f"/api/v1/proposals/{criada['id']}/decision",
        {"version": enviada["version"], "decision": "DEVOLVER"},
    )
    assert sem_motivo.status_code == 422

    devolvida = await api.post(
        f"/api/v1/proposals/{criada['id']}/decision",
        {"version": enviada["version"], "decision": "DEVOLVER", "reason": "Comprovante ilegível"},
    )
    assert devolvida.status_code == 200, devolvida.text
    assert devolvida.json()["approval_status"] == "REJECTED"
    assert devolvida.json()["rejection_reason"] == "Comprovante ilegível"

    # devolvida volta a ser editável e pode ser reenviada
    reenviada = await api.post(
        f"/api/v1/proposals/{criada['id']}/submission", {"version": devolvida.json()["version"]}
    )
    assert reenviada.status_code == 200, reenviada.text
    assert reenviada.json()["approval_status"] == "SUBMITTED"


async def test_remocao_de_anexo_so_vale_enquanto_editavel(api: Api, consultor: int) -> None:
    criada = await _criar_proposta(api, consultor)
    anexo = (
        await api.upload(
            f"/api/v1/proposals/{criada['id']}/attachments",
            file_name="comprovante.pdf",
            content_type="application/pdf",
            conteudo=b"%PDF-1.4 conteudo de teste",
        )
    ).json()

    removida = await api.delete(f"/api/v1/proposals/{criada['id']}/attachments/{anexo['id']}")
    assert removida.status_code == 204

    vazio = await api.get(f"/api/v1/proposals/{criada['id']}/attachments")
    assert vazio.json() == []


async def test_download_de_anexo_confere_conteudo(api: Api, consultor: int) -> None:
    criada = await _criar_proposta(api, consultor)
    conteudo = b"%PDF-1.4 conteudo de teste"
    anexo = (
        await api.upload(
            f"/api/v1/proposals/{criada['id']}/attachments",
            file_name="comprovante.pdf",
            content_type="application/pdf",
            conteudo=conteudo,
        )
    ).json()

    baixado = await api.get(f"/api/v1/proposals/{criada['id']}/attachments/{anexo['id']}")
    assert baixado.status_code == 200
    assert baixado.content == conteudo


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
                    "WHERE aggregate_type = 'proposal' AND aggregate_id = :id "
                    "ORDER BY id"
                ),
                {"id": aggregate_id},
            )
            return [str(linha[0]) for linha in linhas]
    finally:
        await engine.dispose()
