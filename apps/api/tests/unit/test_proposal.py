"""Proposta: comissão, saldo, transições de status e cancelamento (seção 7.4)."""

from __future__ import annotations

from datetime import date

import pytest

from app.modules.commercial.domain.entities.proposal import Proposal
from app.modules.commercial.domain.errors import (
    MotivoDeDevolucaoObrigatorioError,
    PropostaCanceladaError,
    PropostaEmAnaliseError,
    PropostaSemComprovanteError,
    TransicaoDeAprovacaoInvalidaError,
    TransicaoDeStatusInvalidaError,
    ValorDaOperacaoInvalidoError,
)
from app.modules.commercial.domain.value_objects.percentual_tps import PercentualTps
from app.modules.commercial.domain.value_objects.situacao_de_aprovacao import SituacaoDeAprovacao
from app.modules.commercial.domain.value_objects.status_da_proposta import StatusDaProposta
from app.shared.domain.dinheiro import Dinheiro
from app.shared.domain.documento import Documento

CPF = "529.982.247-25"


def nova(operacao: str = "10000.00", tps: str = "10") -> Proposal:
    return Proposal(
        consultant_id=1,
        business_date=date(2026, 8, 12),
        customer_name="  Cliente Exemplo  ",
        customer_document=Documento.normalizar(CPF),
        operation_amount=Dinheiro.de(operacao),
        tps=PercentualTps.de(tps),
    )


def test_nasce_aberta_com_comissao_calculada() -> None:
    proposta = nova()
    assert proposta.status is StatusDaProposta.OPEN
    assert proposta.company_commission_amount == Dinheiro.de("1000.00")
    assert proposta.outstanding_amount == Dinheiro.de("1000.00")
    assert proposta.customer_name == "Cliente Exemplo"


def test_recusa_operacao_nao_positiva() -> None:
    with pytest.raises(ValorDaOperacaoInvalidoError):
        nova(operacao="0.00")


def test_alterar_operacao_recalcula_comissao_e_saldo() -> None:
    proposta = nova()
    proposta.alterar_operacao(
        operation_amount=Dinheiro.de("20000.00"), tps=PercentualTps.de("5")
    )
    assert proposta.company_commission_amount == Dinheiro.de("1000.00")
    assert proposta.outstanding_amount == Dinheiro.de("1000.00")


def test_recebimento_parcial_move_para_parcialmente_paga() -> None:
    proposta = nova()
    proposta.registrar_total_recebido(Dinheiro.de("400.00"))
    assert proposta.status is StatusDaProposta.PARTIALLY_PAID
    assert proposta.outstanding_amount == Dinheiro.de("600.00")


def test_quitacao_dentro_da_tolerancia_de_falta() -> None:
    proposta = nova()
    proposta.registrar_total_recebido(Dinheiro.de("990.00"))
    assert proposta.status is StatusDaProposta.PAID
    # a falta tolerada não fica no "a receber": foi aceita como quitação
    assert proposta.outstanding_amount.zerado


def test_sobrepagamento_quita_mas_fica_sinalizado() -> None:
    proposta = nova()
    proposta.registrar_total_recebido(Dinheiro.de("1200.00"))
    assert proposta.status is StatusDaProposta.PAID
    assert proposta.sobrepago
    # excedente não vira saldo negativo
    assert proposta.outstanding_amount.zerado


def test_estorno_total_reabre_a_proposta() -> None:
    proposta = nova()
    proposta.registrar_total_recebido(Dinheiro.de("1000.00"))
    proposta.registrar_total_recebido(Dinheiro.zero())
    assert proposta.status is StatusDaProposta.OPEN


def test_estorno_parcial_volta_para_parcialmente_paga() -> None:
    proposta = nova()
    proposta.registrar_total_recebido(Dinheiro.de("1000.00"))
    proposta.registrar_total_recebido(Dinheiro.de("300.00"))
    assert proposta.status is StatusDaProposta.PARTIALLY_PAID


def test_cancelamento_e_terminal() -> None:
    proposta = nova()
    proposta.cancelar()
    assert proposta.status is StatusDaProposta.CANCELLED

    with pytest.raises(PropostaCanceladaError):
        proposta.alterar_operacao(
            operation_amount=Dinheiro.de("1.00"), tps=PercentualTps.de("1")
        )


def test_proposta_cancelada_nao_volta_a_ficar_aberta() -> None:
    proposta = nova()
    proposta.cancelar()
    with pytest.raises(TransicaoDeStatusInvalidaError):
        proposta._transicionar(StatusDaProposta.OPEN)


# ---------- aprovação ----------


def test_nasce_em_rascunho() -> None:
    proposta = nova()
    assert proposta.approval_status is SituacaoDeAprovacao.DRAFT
    assert proposta.editavel_pelo_cadastrante


def test_envio_sem_comprovante_e_recusado() -> None:
    proposta = nova()
    with pytest.raises(PropostaSemComprovanteError):
        proposta.enviar_para_aprovacao(quantidade_de_comprovantes=0)


def test_envio_com_comprovante_trava_edicao() -> None:
    proposta = nova()
    proposta.enviar_para_aprovacao(quantidade_de_comprovantes=1)
    assert proposta.approval_status is SituacaoDeAprovacao.SUBMITTED
    assert not proposta.editavel_pelo_cadastrante

    with pytest.raises(PropostaEmAnaliseError):
        proposta.alterar_operacao(operation_amount=Dinheiro.de("1.00"), tps=PercentualTps.de("1"))


def test_aprovacao_e_terminal() -> None:
    proposta = nova()
    proposta.enviar_para_aprovacao(quantidade_de_comprovantes=1)
    proposta.aprovar()
    assert proposta.approval_status is SituacaoDeAprovacao.APPROVED

    with pytest.raises(TransicaoDeAprovacaoInvalidaError):
        proposta.enviar_para_aprovacao(quantidade_de_comprovantes=1)


def test_rejeicao_exige_motivo_e_libera_reenvio() -> None:
    proposta = nova()
    proposta.enviar_para_aprovacao(quantidade_de_comprovantes=1)

    with pytest.raises(MotivoDeDevolucaoObrigatorioError):
        proposta.rejeitar("  ")

    proposta.rejeitar("Comprovante ilegível")
    assert proposta.approval_status is SituacaoDeAprovacao.REJECTED
    assert proposta.rejection_reason == "Comprovante ilegível"
    assert proposta.editavel_pelo_cadastrante

    proposta.enviar_para_aprovacao(quantidade_de_comprovantes=1)
    assert proposta.approval_status is SituacaoDeAprovacao.SUBMITTED
    # o motivo da devolução anterior não sobrevive ao reenvio
    assert proposta.rejection_reason is None
