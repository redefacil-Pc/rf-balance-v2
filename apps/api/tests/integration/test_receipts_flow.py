"""Recebimentos, ponta a ponta.

O fluxo real do negócio: a **Finalização lança a proposta com os valores
recebidos e os comprovantes**; o **Financeiro confere no extrato e aprova**. A
aprovação da proposta é o momento em que o dinheiro passa a valer — não existe
uma segunda decisão sobre o mesmo valor.

Aqui mora dinheiro, então os testes priorizam as regras que **protegem valor**:

- o saldo só se move quando o Financeiro aprova a proposta;
- depois do envio, o conjunto que ele vai conferir não muda por baixo dele;
- estorno tira do saldo e acontece uma vez só;
- chave de idempotência repetida não duplica lançamento — e, reusada com outro
  valor, é recusada em vez de sobrescrever.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import func, select

from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionCalculationSnapshotModel,
    CommissionEntryModel,
)
from app.platform.config.security import CSRF_COOKIE, CSRF_HEADER
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes

pytestmark = pytest.mark.integration

CNPJ_EMPRESA = "04.252.011/0001-10"
CPF_CONSULTOR = "529.982.247-25"
CPF_FINALIZACAO = "390.533.447-05"
CPF_CLIENTE = "111.444.777-35"

PDF = b"%PDF-1.4 comprovante de pagamento"
#: operação de 10.000,00 com TPS de 10% => comissão da empresa de 1.000,00
COMISSAO = "1000.00"


class Api:
    def __init__(self, cliente: AsyncClient) -> None:
        self._cliente = cliente

    @property
    def _csrf(self) -> dict[str, str]:
        return {CSRF_HEADER: self._cliente.cookies[CSRF_COOKIE]}

    async def post(self, caminho: str, corpo: dict[str, Any] | None = None) -> Response:
        return await self._cliente.post(caminho, json=corpo or {}, headers=self._csrf)

    async def get(self, caminho: str, **params: Any) -> Response:
        return await self._cliente.get(caminho, params=params or None)

    async def delete(self, caminho: str) -> Response:
        return await self._cliente.delete(caminho, headers=self._csrf)

    async def anexar(self, caminho: str) -> Response:
        return await self._cliente.post(
            caminho, files={"file": ("c.pdf", PDF, "application/pdf")}, headers=self._csrf
        )

    async def declarar(
        self,
        proposal_id: int,
        *,
        chave: str,
        valor: str = "400.00",
        data: str = "2026-08-12",
        meio: str = "PIX",
        conteudo: bytes = PDF,
        content_type: str = "application/pdf",
    ) -> Response:
        """Declara um valor recebido na proposta, como faz a Finalização."""
        return await self._cliente.post(
            f"/api/v1/proposals/{proposal_id}/receipts",
            data={"amount": valor, "business_date": data, "payment_method": meio},
            files={"proof": ("comprovante.pdf", conteudo, content_type)},
            headers={**self._csrf, "Idempotency-Key": chave},
        )


@pytest.fixture
async def admin(cliente: AsyncClient, admin_semeado: dict[str, str]) -> Api:
    await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )
    return Api(cliente)


@asynccontextmanager
async def _sessao(
    novo_cliente: Callable[[], AsyncClient], email: str, senha: str
) -> AsyncIterator[Api]:
    async with novo_cliente() as cliente:
        entrou = await cliente.post("/api/v1/auth/login", json={"email": email, "password": senha})
        assert entrou.status_code == 200, entrou.text
        yield Api(cliente)


@pytest.fixture
async def empresa(admin: Api) -> int:
    criada = await admin.post(
        "/api/v1/companies",
        {"legal_name": "RF Balance LTDA", "trade_name": "RF Balance", "document": CNPJ_EMPRESA},
    )
    assert criada.status_code == 201, criada.text
    return int(criada.json()["id"])


@pytest.fixture
async def consultor(admin: Api, empresa: int) -> int:
    colaborador = await admin.post(
        "/api/v1/collaborators",
        {
            "company_id": empresa,
            "unit_id": None,
            "full_name": "Maria Consultora",
            "document": CPF_CONSULTOR,
            "tax_regime": "CLT",
            "roles": [{"role": "CONSULTOR", "valid_from": "2026-01-01"}],
        },
    )
    assert colaborador.status_code == 201, colaborador.text
    return int(colaborador.json()["id"])


@pytest.fixture
async def consultor_escalonado(admin: Api, empresa: int) -> int:
    colaborador = await admin.post(
        "/api/v1/collaborators",
        {
            "company_id": empresa,
            "unit_id": None,
            "full_name": "Maria Consultora Escalonada",
            "document": CPF_CONSULTOR,
            "tax_regime": "CLT",
            "roles": [{"role": "CONSULTOR_MEI_ESCALONADO", "valid_from": "2026-01-01"}],
        },
    )
    assert colaborador.status_code == 201, colaborador.text
    return int(colaborador.json()["id"])


@pytest.fixture
async def finalizacao(admin: Api, empresa: int) -> dict[str, Any]:
    """Quem lança a proposta e declara os valores recebidos.

    Perfil de acesso OPERACIONAL **e** função operacional FINALIZACAO — a rota
    exige os dois: a permissão diz o que pode, a função diz quem é.
    """
    conta = await admin.post(
        "/api/v1/users",
        {
            "email": "final@rfbalance.local",
            "full_name": "Fabio Finalizacao",
            "roles": ["OPERACIONAL"],
            "collaborator": {
                "company_id": empresa,
                "unit_id": None,
                "document": CPF_FINALIZACAO,
                "tax_regime": "CLT",
                "function": "FINALIZACAO",
                "valid_from": "2026-01-01",
            },
        },
    )
    assert conta.status_code == 201, conta.text
    corpo: dict[str, Any] = conta.json()
    return corpo


@pytest.fixture
async def financeiro(admin: Api) -> dict[str, Any]:
    """Quem confere no extrato e aprova."""
    conta = await admin.post(
        "/api/v1/users",
        {
            "email": "fin@rfbalance.local",
            "full_name": "Helena Financeiro",
            "roles": ["FINANCEIRO"],
        },
    )
    assert conta.status_code == 201, conta.text
    corpo: dict[str, Any] = conta.json()
    return corpo


async def _rascunho(
    api: Api,
    consultor: int,
    *,
    cliente: str = "Cliente Exemplo",
    operacao: str = "10000.00",
    tps: str = "10",
) -> dict[str, Any]:
    criada = await api.post(
        "/api/v1/proposals",
        {
            "consultant_id": consultor,
            "business_date": "2026-08-12",
            "customer_name": cliente,
            "customer_document": CPF_CLIENTE,
            "operation_amount": operacao,
            "tps_percentage": tps,
        },
    )
    assert criada.status_code == 201, criada.text
    corpo: dict[str, Any] = criada.json()
    return corpo


async def _enviar(api: Api, proposal_id: int, version: int) -> int:
    """Anexa o comprovante exigido e envia para aprovação. Devolve a versão."""
    anexo = await api.anexar(f"/api/v1/proposals/{proposal_id}/attachments")
    assert anexo.status_code == 201, anexo.text
    enviada = await api.post(f"/api/v1/proposals/{proposal_id}/submission", {"version": version})
    assert enviada.status_code == 200, enviada.text
    return int(enviada.json()["version"])


# ---------- declaração pela Finalização ----------


async def test_finalizacao_declara_valor_recebido_na_proposta(
    novo_cliente: Callable[[], AsyncClient], consultor: int, finalizacao: dict[str, Any]
) -> None:
    """O valor entra junto da proposta, não depois de aprovada."""
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)

        declarado = await api.declarar(proposta["id"], chave="chave-declaracao-1")

        assert declarado.status_code == 201, declarado.text
        corpo = declarado.json()
        assert corpo["status"] == "SUBMITTED"
        assert corpo["amount"] == "400.00"
        # declarado ainda não é reconhecido: só a aprovação move o saldo
        assert corpo["proposal_paid_amount"] == "0.00"
        assert corpo["proposal_outstanding_amount"] == COMISSAO

    assert await _contar("outbox_events") == 1


async def test_comprovante_do_recebimento_permite_enviar_a_proposta(
    novo_cliente: Callable[[], AsyncClient], consultor: int, finalizacao: dict[str, Any]
) -> None:
    """O mesmo comprovante serve ao recebimento e à análise da proposta."""
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        declarado = await api.declarar(proposta["id"], chave="comprovante-unico")
        assert declarado.status_code == 201, declarado.text

        enviada = await api.post(
            f"/api/v1/proposals/{proposta['id']}/submission",
            {"version": proposta["version"]},
        )

    assert enviada.status_code == 200, enviada.text
    assert enviada.json()["approval_status"] == "SUBMITTED"


async def test_consultor_nao_declara_recebimento(
    admin: Api, novo_cliente: Callable[[], AsyncClient], consultor: int, empresa: int
) -> None:
    """Perfil sem permissão de recebimento não passa do portão."""
    conta = await admin.post(
        "/api/v1/users",
        {
            "email": "consultor@rfbalance.local",
            "full_name": "Carla Consultora",
            "roles": ["CONSULTOR"],
        },
    )
    proposta = await _rascunho(admin, consultor)

    async with _sessao(
        novo_cliente, "consultor@rfbalance.local", conta.json()["temporary_password"]
    ) as api:
        recusado = await api.declarar(proposta["id"], chave="chave-do-consultor")

    assert recusado.status_code == 403


async def test_operacional_sem_funcao_de_finalizacao_nao_declara(
    admin: Api, novo_cliente: Callable[[], AsyncClient], consultor: int, empresa: int
) -> None:
    """A permissão abre a porta; a função operacional decide quem entra."""
    conta = await admin.post(
        "/api/v1/users",
        {
            "email": "bko@rfbalance.local",
            "full_name": "Gisele BKO",
            "roles": ["OPERACIONAL"],
            "collaborator": {
                "company_id": empresa,
                "unit_id": None,
                "document": "168.995.350-09",
                "tax_regime": "CLT",
                "function": "BKO",
                "valid_from": "2026-01-01",
            },
        },
    )
    assert conta.status_code == 201, conta.text
    proposta = await _rascunho(admin, consultor)

    async with _sessao(
        novo_cliente, "bko@rfbalance.local", conta.json()["temporary_password"]
    ) as api:
        recusado = await api.declarar(proposta["id"], chave="chave-do-bko")

    assert recusado.status_code == 403
    assert recusado.json()["type"].endswith("receipt-launcher-not-allowed")


async def test_proposta_enviada_congela_os_recebimentos(
    novo_cliente: Callable[[], AsyncClient], consultor: int, finalizacao: dict[str, Any]
) -> None:
    """Depois do envio, o conjunto que o Financeiro vai conferir não muda."""
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        await api.declarar(proposta["id"], chave="chave-antes-do-envio")
        await _enviar(api, proposta["id"], proposta["version"])

        tardio = await api.declarar(proposta["id"], chave="chave-depois-do-envio")

    assert tardio.status_code == 409
    assert tardio.json()["type"].endswith("invalid-receipt-flow")


async def test_comprovante_de_tipo_nao_aceito_e_recusado(
    novo_cliente: Callable[[], AsyncClient], consultor: int, finalizacao: dict[str, Any]
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        recusado = await api.declarar(
            proposta["id"],
            chave="chave-tipo-invalido",
            conteudo=b"col1;col2",
            content_type="text/csv",
        )

    assert recusado.status_code == 422
    assert recusado.json()["type"].endswith("invalid-receipt")


async def test_data_futura_nao_e_aceita(
    novo_cliente: Callable[[], AsyncClient], consultor: int, finalizacao: dict[str, Any]
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        recusado = await api.declarar(proposta["id"], chave="chave-data-futura", data="2999-01-01")

    assert recusado.status_code == 422
    assert recusado.json()["type"].endswith("invalid-receipt")


async def test_declaracoes_nao_ultrapassam_tolerancia_de_sobrepagamento(
    novo_cliente: Callable[[], AsyncClient], consultor: int, finalizacao: dict[str, Any]
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        assert (
            await api.declarar(proposta["id"], chave="chave-limite-1", valor="1000.00")
        ).status_code == 201
        excedente = await api.declarar(proposta["id"], chave="chave-limite-2", valor="100.01")

    assert excedente.status_code == 422
    assert excedente.json()["type"].endswith("invalid-receipt")


async def test_remocao_corrige_o_que_foi_digitado_errado(
    novo_cliente: Callable[[], AsyncClient], consultor: int, finalizacao: dict[str, Any]
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        errado = (await api.declarar(proposta["id"], chave="chave-errada", valor="40.00")).json()

        removido = await api.delete(f"/api/v1/receipts/{errado['id']}")
        assert removido.status_code == 204

        restantes = await api.get("/api/v1/receipts", proposal_id=proposta["id"])
        assert restantes.json()["items"] == []


async def test_remocao_nao_vale_depois_do_envio(
    novo_cliente: Callable[[], AsyncClient], consultor: int, finalizacao: dict[str, Any]
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        declarado = (await api.declarar(proposta["id"], chave="chave-congelada")).json()
        await _enviar(api, proposta["id"], proposta["version"])

        recusado = await api.delete(f"/api/v1/receipts/{declarado['id']}")

    assert recusado.status_code == 409


# ---------- idempotência ----------


async def test_chave_repetida_nao_duplica_declaracao(
    novo_cliente: Callable[[], AsyncClient], consultor: int, finalizacao: dict[str, Any]
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        primeiro = await api.declarar(proposta["id"], chave="chave-repetida")
        segundo = await api.declarar(proposta["id"], chave="chave-repetida")

        assert segundo.json()["id"] == primeiro.json()["id"]
        listagem = await api.get("/api/v1/receipts", proposal_id=proposta["id"])
        assert len(listagem.json()["items"]) == 1


async def test_chave_reutilizada_com_outro_valor_e_recusada(
    novo_cliente: Callable[[], AsyncClient], consultor: int, finalizacao: dict[str, Any]
) -> None:
    """A chave identifica um pedido. Reusá-la com outro valor sobrescreveria um
    lançamento financeiro em silêncio."""
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        await api.declarar(proposta["id"], chave="chave-conflitante", valor="400.00")
        conflito = await api.declarar(proposta["id"], chave="chave-conflitante", valor="900.00")

    assert conflito.status_code == 409
    assert conflito.json()["type"].endswith("idempotency-key-conflict")


# ---------- reconhecimento na aprovação ----------


async def test_aprovacao_da_proposta_reconhece_o_valor_declarado(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    """O ponto central: uma aprovação só, e é ela que move o dinheiro."""
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        recebimento = (
            await api.declarar(
                proposta["id"], chave="chave-reconhecimento", valor="400.00"
            )
        ).json()
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        aprovada = await api.post(
            f"/api/v1/proposals/{proposta['id']}/decision",
            {"version": versao, "decision": "APROVAR"},
        )
        assert aprovada.status_code == 200, aprovada.text

        detalhe = (await api.get(f"/api/v1/proposals/{proposta['id']}")).json()
        memoria_recebimento = (
            await api.get(
                f"/api/v1/receipts/{recebimento['id']}/commission-calculations"
            )
        ).json()
        memoria_proposta = (
            await api.get(f"/api/v1/proposals/{proposta['id']}/commission-calculations")
        ).json()

    assert detalhe["paid_amount"] == "400.00"
    assert detalhe["outstanding_amount"] == "600.00"
    assert detalhe["status"] == "PARTIALLY_PAID"
    assert detalhe["approval_status"] == "APPROVED"
    assert memoria_recebimento["total_net_amount"] == "24.00"
    assert memoria_recebimento["items"][0]["inputs"]["receipt_eligible_amount"] == "400.00"
    assert memoria_recebimento["items"][0]["outputs"]["percentage"] == "6.000000"
    assert memoria_proposta == memoria_recebimento

    engine = criar_engine(get_settings().database)
    try:
        async with criar_fabrica_de_sessoes(engine)() as session:
            lancamento = await session.scalar(
                select(CommissionEntryModel).where(
                    CommissionEntryModel.proposal_id == proposta["id"]
                )
            )
            assert lancamento is not None
            assert lancamento.beneficiary_id == consultor
            assert lancamento.amount == 24
            snapshot = await session.get(CommissionCalculationSnapshotModel, lancamento.snapshot_id)
            assert snapshot is not None
            assert snapshot.inputs["rule_set_version"] == "2026.1"
            assert snapshot.outputs["recognized_production"] == "4000.00"
    finally:
        await engine.dispose()


async def test_escalonado_rateia_faixas_e_recalcula_o_mes_no_estorno(
    novo_cliente: Callable[[], AsyncClient],
    consultor_escalonado: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        primeira = await _rascunho(
            api,
            consultor_escalonado,
            cliente="Cliente faixa um",
            operacao="70000.00",
            tps="35",
        )
        recibo_um = (
            await api.declarar(primeira["id"], chave="escalonado-faixa-1", valor="24500.00")
        ).json()
        versao_um = await _enviar(api, primeira["id"], primeira["version"])

        segunda = await _rascunho(
            api,
            consultor_escalonado,
            cliente="Cliente cruza faixa",
            operacao="20000.00",
            tps="35",
        )
        await api.declarar(segunda["id"], chave="escalonado-cruza-faixa", valor="7000.00")
        versao_dois = await _enviar(api, segunda["id"], segunda["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        assert (
            await api.post(
                f"/api/v1/proposals/{primeira['id']}/decision",
                {"version": versao_um, "decision": "APROVAR"},
            )
        ).status_code == 200
        assert (
            await api.post(
                f"/api/v1/proposals/{segunda['id']}/decision",
                {"version": versao_dois, "decision": "APROVAR"},
            )
        ).status_code == 200

    engine = criar_engine(get_settings().database)
    try:
        async with criar_fabrica_de_sessoes(engine)() as session:
            snapshots = list(
                (
                    await session.scalars(
                        select(CommissionCalculationSnapshotModel)
                        .where(
                            CommissionCalculationSnapshotModel.beneficiary_id
                            == consultor_escalonado,
                            CommissionCalculationSnapshotModel.strategy == "SCALED_CONSULTANT",
                        )
                        .order_by(CommissionCalculationSnapshotModel.receipt_id)
                    )
                ).all()
            )
            assert len(snapshots) == 2
            assert snapshots[0].strategy_config_id == 1
            assert snapshots[1].outputs["commission_amount"] == "665.00"
            assert [item["recognized_production"] for item in snapshots[1].outputs["segments"]] == [
                "5000.00",
                "15000.00",
            ]
    finally:
        await engine.dispose()

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        estornado = await api.post(
            f"/api/v1/receipts/{recibo_um['id']}/reversal",
            {"reason": "Estorno para recalcular as faixas", "business_date": "2026-08-13"},
        )
        assert estornado.status_code == 200, estornado.text

    engine = criar_engine(get_settings().database)
    try:
        async with criar_fabrica_de_sessoes(engine)() as session:
            saldo = await session.scalar(
                select(func.sum(CommissionEntryModel.amount))
                .join(
                    CommissionCalculationSnapshotModel,
                    CommissionCalculationSnapshotModel.id == CommissionEntryModel.snapshot_id,
                )
                .where(
                    CommissionCalculationSnapshotModel.beneficiary_id == consultor_escalonado,
                    CommissionCalculationSnapshotModel.strategy == "SCALED_CONSULTANT",
                )
            )
            assert saldo == 560
    finally:
        await engine.dispose()


async def test_valor_declarado_que_quita_leva_a_proposta_a_paga(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        await api.declarar(proposta["id"], chave="chave-quitacao", valor=COMISSAO)
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        await api.post(
            f"/api/v1/proposals/{proposta['id']}/decision",
            {"version": versao, "decision": "APROVAR"},
        )
        detalhe = (await api.get(f"/api/v1/proposals/{proposta['id']}")).json()

    assert detalhe["status"] == "PAID"
    assert detalhe["outstanding_amount"] == "0.00"


async def test_varios_recebimentos_somam_no_reconhecimento(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    """Pagamento em parcelas: cada uma com o seu comprovante."""
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        await api.declarar(proposta["id"], chave="chave-parcela-1", valor="600.00")
        await api.declarar(proposta["id"], chave="chave-parcela-2", valor="400.00")
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        await api.post(
            f"/api/v1/proposals/{proposta['id']}/decision",
            {"version": versao, "decision": "APROVAR"},
        )
        detalhe = (await api.get(f"/api/v1/proposals/{proposta['id']}")).json()

    assert detalhe["paid_amount"] == COMISSAO
    assert detalhe["status"] == "PAID"


async def test_devolucao_da_proposta_nao_reconhece_nada(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    """Se o Financeiro não achou o pagamento no extrato, nada entra no saldo."""
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        await api.declarar(proposta["id"], chave="chave-devolvida", valor=COMISSAO)
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        devolvida = await api.post(
            f"/api/v1/proposals/{proposta['id']}/decision",
            {
                "version": versao,
                "decision": "DEVOLVER",
                "reason": "Pagamento não localizado no extrato",
            },
        )
        assert devolvida.status_code == 200, devolvida.text
        detalhe = (await api.get(f"/api/v1/proposals/{proposta['id']}")).json()

    assert detalhe["paid_amount"] == "0.00"
    assert detalhe["outstanding_amount"] == COMISSAO
    assert detalhe["approval_status"] == "REJECTED"


async def test_devolvida_volta_a_aceitar_correcao_e_reenvio(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        await api.declarar(proposta["id"], chave="chave-correcao-1", valor="100.00")
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        devolvida = await api.post(
            f"/api/v1/proposals/{proposta['id']}/decision",
            {"version": versao, "decision": "DEVOLVER", "reason": "Valor divergente"},
        )
        versao = devolvida.json()["version"]

    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        # devolvida volta a ser editável: dá para declarar o valor certo
        corrigido = await api.declarar(proposta["id"], chave="chave-correcao-2", valor="900.00")
        assert corrigido.status_code == 201, corrigido.text


# ---------- pagamento posterior, com saldo em aberto ----------


async def test_proposta_aprovada_com_saldo_aceita_novo_pagamento(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    """O cliente pagou parte agora e o resto depois — o restante precisa entrar."""
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        await api.declarar(proposta["id"], chave="chave-entrada", valor="400.00")
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        await api.post(
            f"/api/v1/proposals/{proposta['id']}/decision",
            {"version": versao, "decision": "APROVAR"},
        )
        detalhe = (await api.get(f"/api/v1/proposals/{proposta['id']}")).json()
        assert detalhe["status"] == "PARTIALLY_PAID"
        assert detalhe["outstanding_amount"] == "600.00"

    # semanas depois, o cliente paga o restante
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        segundo = await api.declarar(proposta["id"], chave="chave-saldo", valor="600.00")
        assert segundo.status_code == 201, segundo.text
        recebimento = segundo.json()

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        conferido = await api.post(
            f"/api/v1/receipts/{recebimento['id']}/decision", {"decision": "APPROVE"}
        )

    assert conferido.status_code == 200, conferido.text
    assert conferido.json()["proposal_paid_amount"] == COMISSAO
    assert conferido.json()["proposal_outstanding_amount"] == "0.00"
    assert conferido.json()["proposal_status"] == "PAID"


async def test_proposta_quitada_nao_aceita_mais_recebimento(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    """Sem saldo não há o que pagar — e a mensagem diz isso, não um genérico."""
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        await api.declarar(proposta["id"], chave="chave-quita-tudo", valor=COMISSAO)
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        await api.post(
            f"/api/v1/proposals/{proposta['id']}/decision",
            {"version": versao, "decision": "APROVAR"},
        )

    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        excedente = await api.declarar(proposta["id"], chave="chave-excedente", valor="50.00")

    assert excedente.status_code == 409
    assert "quitada" in excedente.json()["detail"]


async def test_estorno_reabre_a_janela_de_recebimento(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    """Se o pagamento voltou pelo banco, a proposta volta a ter saldo — e a
    declaração do pagamento correto tem de caber."""
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        recebimento = (
            await api.declarar(proposta["id"], chave="chave-reabre", valor=COMISSAO)
        ).json()
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        await api.post(
            f"/api/v1/proposals/{proposta['id']}/decision",
            {"version": versao, "decision": "APROVAR"},
        )
        await api.post(
            f"/api/v1/receipts/{recebimento['id']}/reversal",
            {"reason": "Pagamento devolvido pelo banco", "business_date": "2026-08-13"},
        )

    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        refeito = await api.declarar(proposta["id"], chave="chave-refeita", valor=COMISSAO)

    assert refeito.status_code == 201, refeito.text


async def test_quem_declarou_nao_confere_o_proprio_lancamento(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    """Segregação de funções no pagamento posterior: declarar e conferir são de
    pessoas diferentes."""
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        await api.declarar(proposta["id"], chave="chave-segregacao", valor="400.00")
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        await api.post(
            f"/api/v1/proposals/{proposta['id']}/decision",
            {"version": versao, "decision": "APROVAR"},
        )
        # o próprio Financeiro declara o pagamento seguinte...
        proprio = (
            await api.declarar(proposta["id"], chave="chave-do-financeiro", valor="600.00")
        ).json()
        # ...e não pode conferir o que ele mesmo lançou
        recusado = await api.post(
            f"/api/v1/receipts/{proprio['id']}/decision", {"decision": "APPROVE"}
        )

    assert recusado.status_code == 403
    assert recusado.json()["type"].endswith("receipt-self-approval")


async def test_declarado_antes_do_envio_nao_tem_decisao_avulsa(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    """Um caminho só para cada momento: o que entra antes do envio é conferido
    junto da proposta, e não por fora."""
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        recebimento = (
            await api.declarar(proposta["id"], chave="chave-sem-avulsa", valor="400.00")
        ).json()

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        recusado = await api.post(
            f"/api/v1/receipts/{recebimento['id']}/decision", {"decision": "APPROVE"}
        )

    assert recusado.status_code == 409
    assert "aprovação da proposta" in recusado.json()["detail"]


# ---------- atomicidade e concorrência ----------


async def test_dois_reconhecimentos_simultaneos_preservam_a_soma(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        aprovada = await api.post(
            f"/api/v1/proposals/{proposta['id']}/decision",
            {"version": versao, "decision": "APROVAR"},
        )
        assert aprovada.status_code == 200, aprovada.text

    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        um = (await api.declarar(proposta["id"], chave="concorrente-1", valor="400.00")).json()
        dois = (await api.declarar(proposta["id"], chave="concorrente-2", valor="500.00")).json()

    async with (
        _sessao(novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]) as api_um,
        _sessao(novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]) as api_dois,
    ):
        respostas = await asyncio.gather(
            api_um.post(f"/api/v1/receipts/{um['id']}/decision", {"decision": "APPROVE"}),
            api_dois.post(f"/api/v1/receipts/{dois['id']}/decision", {"decision": "APPROVE"}),
        )
        detalhe = await api_um.get(f"/api/v1/proposals/{proposta['id']}")

    assert [resposta.status_code for resposta in respostas] == [200, 200]
    assert detalhe.json()["paid_amount"] == "900.00"
    assert detalhe.json()["outstanding_amount"] == "100.00"


async def test_falha_na_outbox_reverte_recebimento_e_auditoria(
    monkeypatch: pytest.MonkeyPatch,
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
) -> None:
    from app.platform.bus.outbox_recorder import SqlOutboxRecorder

    def falhar(*args: Any, **kwargs: Any) -> None:
        del args, kwargs
        raise RuntimeError("falha simulada na outbox")

    monkeypatch.setattr(SqlOutboxRecorder, "registrar", falhar)
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        auditorias_antes = await _contar("audit_events")
        with pytest.raises(RuntimeError, match="falha simulada"):
            await api.declarar(proposta["id"], chave="falha-outbox")

    assert await _contar("receipts") == 0
    assert await _contar("audit_events") == auditorias_antes


# ---------- estorno ----------


async def test_estorno_devolve_o_valor_ao_saldo_em_aberto(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    """Dinheiro que voltou pelo banco deixa de contar — e o histórico fica."""
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        recebimento = (
            await api.declarar(proposta["id"], chave="chave-estorno", valor=COMISSAO)
        ).json()
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        await api.post(
            f"/api/v1/proposals/{proposta['id']}/decision",
            {"version": versao, "decision": "APROVAR"},
        )

        estornado = await api.post(
            f"/api/v1/receipts/{recebimento['id']}/reversal",
            {"reason": "Pagamento devolvido pelo banco", "business_date": "2026-08-13"},
        )

    assert estornado.status_code == 200, estornado.text
    assert estornado.json()["proposal_paid_amount"] == "0.00"
    assert estornado.json()["proposal_outstanding_amount"] == COMISSAO
    assert estornado.json()["proposal_status"] == "OPEN"


async def test_estornos_parciais_preservam_o_restante_reconhecido(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        recebimento = (
            await api.declarar(proposta["id"], chave="chave-estorno-parcial", valor=COMISSAO)
        ).json()
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        await api.post(
            f"/api/v1/proposals/{proposta['id']}/decision",
            {"version": versao, "decision": "APROVAR"},
        )
        primeiro = await api.post(
            f"/api/v1/receipts/{recebimento['id']}/reversal",
            {"reason": "Devolução parcial", "business_date": "2026-08-13", "amount": "250.00"},
        )
        segundo = await api.post(
            f"/api/v1/receipts/{recebimento['id']}/reversal",
            {"reason": "Segunda devolução", "business_date": "2026-08-13", "amount": "150.00"},
        )
        listagem = await api.get("/api/v1/receipts", proposal_id=proposta["id"])

    assert primeiro.status_code == 200, primeiro.text
    assert primeiro.json()["proposal_paid_amount"] == "750.00"
    assert segundo.status_code == 200, segundo.text
    assert segundo.json()["proposal_paid_amount"] == "600.00"
    assert segundo.json()["proposal_outstanding_amount"] == "400.00"
    listado = listagem.json()["items"][0]
    assert listado["reversed"] is True
    assert listado["reversed_amount"] == "400.00"
    assert listado["net_amount"] == "600.00"
    engine = criar_engine(get_settings().database)
    try:
        async with criar_fabrica_de_sessoes(engine)() as session:
            quantidade, saldo = (
                await session.execute(
                    select(
                        func.count(CommissionEntryModel.id),
                        func.sum(CommissionEntryModel.amount),
                    ).where(CommissionEntryModel.receipt_id == recebimento["id"])
                )
            ).one()
            assert quantidade == 3
            assert saldo == 36
    finally:
        await engine.dispose()


async def test_estorno_reabre_teto_para_recebimento_substituto_e_nova_comissao(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        original = (
            await api.declarar(proposta["id"], chave="chave-original-substituida", valor=COMISSAO)
        ).json()
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        assert (
            await api.post(
                f"/api/v1/proposals/{proposta['id']}/decision",
                {"version": versao, "decision": "APROVAR"},
            )
        ).status_code == 200
        assert (
            await api.post(
                f"/api/v1/receipts/{original['id']}/reversal",
                {
                    "reason": "Pagamento devolvido e substituido",
                    "business_date": "2026-08-13",
                    "amount": "500.00",
                },
            )
        ).status_code == 200

    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        substituto = (
            await api.declarar(
                proposta["id"], chave="chave-recebimento-substituto", valor="500.00"
            )
        ).json()

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        aprovado = await api.post(
            f"/api/v1/receipts/{substituto['id']}/decision", {"decision": "APPROVE"}
        )
        assert aprovado.status_code == 200, aprovado.text

    engine = criar_engine(get_settings().database)
    try:
        async with criar_fabrica_de_sessoes(engine)() as session:
            saldo = await session.scalar(
                select(func.sum(CommissionEntryModel.amount))
                .join(
                    CommissionCalculationSnapshotModel,
                    CommissionCalculationSnapshotModel.id == CommissionEntryModel.snapshot_id,
                )
                .where(
                    CommissionCalculationSnapshotModel.proposal_id == proposta["id"],
                    CommissionCalculationSnapshotModel.strategy == "STANDARD_CONSULTANT",
                )
            )
            snapshot_substituto = await session.scalar(
                select(CommissionCalculationSnapshotModel).where(
                    CommissionCalculationSnapshotModel.receipt_id == substituto["id"],
                    CommissionCalculationSnapshotModel.strategy == "STANDARD_CONSULTANT",
                )
            )
            assert saldo == 60
            assert snapshot_substituto is not None
            assert snapshot_substituto.inputs["receipt_eligible_amount"] == "500.00"
    finally:
        await engine.dispose()


async def test_estorno_de_sobrepagamento_nao_reduz_comissao(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        recebimento = (
            await api.declarar(proposta["id"], chave="chave-sobrepagamento", valor="1050.00")
        ).json()
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        assert (
            await api.post(
                f"/api/v1/proposals/{proposta['id']}/decision",
                {"version": versao, "decision": "APROVAR"},
            )
        ).status_code == 200
        estornado = await api.post(
            f"/api/v1/receipts/{recebimento['id']}/reversal",
            {
                "reason": "Devolucao somente do excedente",
                "business_date": "2026-08-13",
                "amount": "50.00",
            },
        )
        assert estornado.status_code == 200, estornado.text

    engine = criar_engine(get_settings().database)
    try:
        async with criar_fabrica_de_sessoes(engine)() as session:
            saldo = await session.scalar(
                select(func.sum(CommissionEntryModel.amount))
                .join(
                    CommissionCalculationSnapshotModel,
                    CommissionCalculationSnapshotModel.id == CommissionEntryModel.snapshot_id,
                )
                .where(
                    CommissionCalculationSnapshotModel.proposal_id == proposta["id"],
                    CommissionCalculationSnapshotModel.strategy == "STANDARD_CONSULTANT",
                )
            )
            assert saldo == 60
    finally:
        await engine.dispose()


async def test_estorno_exige_recebimento_ja_reconhecido(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    """Não se estorna o que ainda nem foi conferido."""
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        recebimento = (await api.declarar(proposta["id"], chave="chave-estorno-cedo")).json()

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        recusado = await api.post(
            f"/api/v1/receipts/{recebimento['id']}/reversal",
            {"reason": "Tentativa indevida", "business_date": "2026-08-13"},
        )

    assert recusado.status_code == 409
    assert recusado.json()["type"].endswith("invalid-receipt-flow")


async def test_estorno_acontece_uma_vez_so(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    """Estorno repetido subtrairia o mesmo valor duas vezes."""
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        recebimento = (await api.declarar(proposta["id"], chave="chave-estorno-duplo")).json()
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        await api.post(
            f"/api/v1/proposals/{proposta['id']}/decision",
            {"version": versao, "decision": "APROVAR"},
        )
        caminho = f"/api/v1/receipts/{recebimento['id']}/reversal"
        corpo = {"reason": "Pagamento devolvido", "business_date": "2026-08-13"}

        assert (await api.post(caminho, corpo)).status_code == 200
        repetido = await api.post(caminho, corpo)

    assert repetido.status_code == 409


async def test_estorno_e_exclusivo_do_financeiro(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        recebimento = (await api.declarar(proposta["id"], chave="chave-estorno-final")).json()
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        await api.post(
            f"/api/v1/proposals/{proposta['id']}/decision",
            {"version": versao, "decision": "APROVAR"},
        )

    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        recusado = await api.post(
            f"/api/v1/receipts/{recebimento['id']}/reversal",
            {"reason": "Nao deveria conseguir", "business_date": "2026-08-13"},
        )

    assert recusado.status_code == 403


# ---------- consulta e trilha ----------


async def test_listagem_traz_situacao_estorno_e_autoria(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        um = (await api.declarar(proposta["id"], chave="chave-lista-1", valor="100.00")).json()
        await api.declarar(proposta["id"], chave="chave-lista-2", valor="200.00")
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        await api.post(
            f"/api/v1/proposals/{proposta['id']}/decision",
            {"version": versao, "decision": "APROVAR"},
        )
        await api.post(
            f"/api/v1/receipts/{um['id']}/reversal",
            {"reason": "Estorno para conferencia", "business_date": "2026-08-13"},
        )

        todos = await api.get("/api/v1/receipts", proposal_id=proposta["id"])

    itens = {item["id"]: item for item in todos.json()["items"]}
    assert len(itens) == 2
    assert itens[um["id"]]["reversed"] is True
    assert itens[um["id"]]["reversed_amount"] == "100.00"
    assert itens[um["id"]]["net_amount"] == "0.00"
    assert itens[um["id"]]["reversal_reason"] == "Estorno para conferencia"
    # quem declarou é a Finalização, não o Financeiro que aprovou
    assert itens[um["id"]]["creator_name"] == "Fabio Finalizacao"
    assert itens[um["id"]]["customer_name"] == "Cliente Exemplo"


async def test_download_do_comprovante_devolve_o_arquivo(
    novo_cliente: Callable[[], AsyncClient], consultor: int, finalizacao: dict[str, Any]
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        recebimento = (await api.declarar(proposta["id"], chave="chave-comprovante")).json()

        baixado = await api.get(f"/api/v1/receipts/{recebimento['id']}/proof")

    assert baixado.status_code == 200
    assert baixado.content == PDF


async def test_declaracao_e_reconhecimento_geram_trilha(
    novo_cliente: Callable[[], AsyncClient],
    consultor: int,
    finalizacao: dict[str, Any],
    financeiro: dict[str, Any],
) -> None:
    async with _sessao(
        novo_cliente, "final@rfbalance.local", finalizacao["temporary_password"]
    ) as api:
        proposta = await _rascunho(api, consultor)
        recebimento = (await api.declarar(proposta["id"], chave="chave-trilha")).json()
        versao = await _enviar(api, proposta["id"], proposta["version"])

    async with _sessao(
        novo_cliente, "fin@rfbalance.local", financeiro["temporary_password"]
    ) as api:
        await api.post(
            f"/api/v1/proposals/{proposta['id']}/decision",
            {"version": versao, "decision": "APROVAR"},
        )
        await api.post(
            f"/api/v1/receipts/{recebimento['id']}/reversal",
            {"reason": "Pagamento devolvido", "business_date": "2026-08-13"},
        )

    do_recebimento = await _acoes("receipt", str(recebimento["id"]))
    da_proposta = await _acoes("proposal", str(proposta["id"]))

    assert do_recebimento == ["receipt.submitted", "receipt.reversed"]
    # o reconhecimento do dinheiro fica na trilha da proposta, junto da decisão
    assert "proposal.approved" in da_proposta


async def _acoes(aggregate_type: str, aggregate_id: str) -> list[str]:
    from sqlalchemy import text

    from app.platform.config.settings import get_settings
    from app.platform.db.engine import criar_engine

    engine = criar_engine(get_settings().database)
    try:
        async with engine.connect() as conexao:
            linhas = await conexao.execute(
                text(
                    "SELECT action FROM audit_events "
                    "WHERE aggregate_type = :tipo AND aggregate_id = :id ORDER BY id"
                ),
                {"tipo": aggregate_type, "id": aggregate_id},
            )
            return [str(linha[0]) for linha in linhas]
    finally:
        await engine.dispose()


async def _contar(tabela: str) -> int:
    from sqlalchemy import text

    from app.platform.config.settings import get_settings
    from app.platform.db.engine import criar_engine

    assert tabela in {"receipts", "audit_events", "outbox_events"}
    engine = criar_engine(get_settings().database)
    try:
        async with engine.connect() as conexao:
            total = await conexao.scalar(text(f"SELECT COUNT(*) FROM {tabela}"))
            return int(total or 0)
    finally:
        await engine.dispose()
