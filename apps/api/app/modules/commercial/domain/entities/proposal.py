"""Proposta: o aggregate comercial único (seção 7.4).

Toda regra que decide dinheiro da proposta está aqui — comissão da empresa, saldo
em aberto e status. O handler orquestra e persiste; o SQL apenas guarda o
resultado. `sales`/`propostas` do legado não têm entidade própria: entram pelo
ACL do importador e viram `Proposal`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.modules.commercial.domain.errors import (
    MotivoDeDevolucaoObrigatorioError,
    PropostaCanceladaError,
    PropostaEmAnaliseError,
    PropostaSemComprovanteError,
    TransicaoDeAprovacaoInvalidaError,
    TransicaoDeStatusInvalidaError,
    ValorDaOperacaoInvalidoError,
)
from app.modules.commercial.domain.policies import settlement_tolerance_policy as tolerancia
from app.modules.commercial.domain.value_objects.percentual_tps import PercentualTps
from app.modules.commercial.domain.value_objects.situacao_de_aprovacao import (
    EDITAVEIS,
    SituacaoDeAprovacao,
)
from app.modules.commercial.domain.value_objects.situacao_de_aprovacao import (
    permite as aprovacao_permite,
)
from app.modules.commercial.domain.value_objects.status_da_proposta import (
    StatusDaProposta,
    permite,
)
from app.shared.domain.dinheiro import Dinheiro
from app.shared.domain.documento import Documento


@dataclass(slots=True)
class Proposal:
    consultant_id: int
    business_date: date
    customer_name: str
    customer_document: Documento
    operation_amount: Dinheiro
    tps: PercentualTps
    id: int | None = None
    external_id: str | None = None
    bko_collaborator_id: int | None = None
    finalizer_collaborator_id: int | None = None
    paid_amount: Dinheiro = field(default_factory=Dinheiro.zero)
    status: StatusDaProposta = StatusDaProposta.OPEN
    #: fluxo cadastro → financeiro; nasce em rascunho
    approval_status: SituacaoDeAprovacao = SituacaoDeAprovacao.DRAFT
    rejection_reason: str | None = None
    #: versão da política de tolerância aplicada na última classificação
    tolerance_policy_version: str = tolerancia.VERSAO_VIGENTE
    version: int = 1

    def __post_init__(self) -> None:
        if not self.operation_amount.positivo:
            raise ValorDaOperacaoInvalidoError("O valor da operação deve ser maior que zero.")
        self.customer_name = self.customer_name.strip()

    @property
    def company_commission_amount(self) -> Dinheiro:
        """Comissão da empresa = operação * TPS / 100 (seção 7.4)."""
        return self.tps.aplicar_sobre(self.operation_amount)

    @property
    def outstanding_amount(self) -> Dinheiro:
        """Quanto ainda se espera receber.

        Zero quando a proposta está quitada ou cancelada — inclusive quando faltou
        um valor dentro da tolerância: essa falta foi aceita, e somar esses
        centavos no "a receber" do dashboard produziria uma carteira fantasma.
        Nunca negativo: excedente é sobrepagamento, não saldo devedor invertido.
        """
        if self.status in (StatusDaProposta.PAID, StatusDaProposta.CANCELLED):
            return Dinheiro.zero()
        falta = self.company_commission_amount - self.paid_amount
        return falta if falta.positivo else Dinheiro.zero()

    @property
    def sobrepago(self) -> bool:
        return self._classificacao() is tolerancia.ResultadoDeQuitacao.SOBREPAGAMENTO

    def enviar_para_aprovacao(self, *, quantidade_de_comprovantes: int) -> None:
        """Envia ao financeiro. Sem comprovante não envia: quem aprova precisa
        conferir o pagamento do cliente contra o valor declarado."""
        self._exigir_ativa()
        self._transicionar_aprovacao(SituacaoDeAprovacao.SUBMITTED)
        if quantidade_de_comprovantes < 1:
            raise PropostaSemComprovanteError()
        self.approval_status = SituacaoDeAprovacao.SUBMITTED
        # o motivo da devolução anterior deixa de valer no reenvio
        self.rejection_reason = None

    def aprovar(self) -> None:
        self._exigir_ativa()
        self._transicionar_aprovacao(SituacaoDeAprovacao.APPROVED)
        self.approval_status = SituacaoDeAprovacao.APPROVED

    def rejeitar(self, motivo: str) -> None:
        """Devolve para correção. Motivo é obrigatório: quem cadastrou precisa
        saber o que corrigir — devolução muda sem explicação é retrabalho cego."""
        self._exigir_ativa()
        self._transicionar_aprovacao(SituacaoDeAprovacao.REJECTED)
        if len(motivo.strip()) < 3:
            raise MotivoDeDevolucaoObrigatorioError(
                "Explique o motivo da devolução para quem vai corrigir."
            )
        self.approval_status = SituacaoDeAprovacao.REJECTED
        self.rejection_reason = motivo.strip()

    @property
    def editavel_pelo_cadastrante(self) -> bool:
        return self.approval_status in EDITAVEIS

    def alterar_operacao(self, *, operation_amount: Dinheiro, tps: PercentualTps) -> None:
        """Altera valor e TPS. Quem verifica se o período está aberto é o caso de
        uso — a proposta não conhece o calendário contábil."""
        self._exigir_ativa()
        if self.approval_status is SituacaoDeAprovacao.SUBMITTED:
            raise PropostaEmAnaliseError()
        if not operation_amount.positivo:
            raise ValorDaOperacaoInvalidoError("O valor da operação deve ser maior que zero.")
        self.operation_amount = operation_amount
        self.tps = tps
        self._reavaliar_status()

    def registrar_total_recebido(self, total: Dinheiro) -> None:
        """Consolida o total elegível vindo de `receivables` e reavalia o status.

        Recebe o **total**, não a parcela: assim estorno e recebimento usam o
        mesmo caminho e o cache não depende de somar incrementos sem perder um.
        """
        self._exigir_ativa()
        self.paid_amount = total
        self._reavaliar_status()

    def cancelar(self) -> None:
        self._transicionar(StatusDaProposta.CANCELLED)

    def _reavaliar_status(self) -> None:
        politica = tolerancia.vigente()
        self.tolerance_policy_version = politica.versao
        resultado = politica.classificar(
            esperado=self.company_commission_amount, recebido=self.paid_amount
        )
        if resultado is tolerancia.ResultadoDeQuitacao.EM_ABERTO:
            destino = (
                StatusDaProposta.OPEN
                if self.paid_amount.zerado
                else StatusDaProposta.PARTIALLY_PAID
            )
        else:
            # sobrepagamento também quita: o excedente vira exceção sinalizada,
            # não impede a proposta de estar paga
            destino = StatusDaProposta.PAID
        self._transicionar(destino)

    def _classificacao(self) -> tolerancia.ResultadoDeQuitacao:
        return tolerancia.resolver(self.tolerance_policy_version).classificar(
            esperado=self.company_commission_amount, recebido=self.paid_amount
        )

    def _transicionar_aprovacao(self, destino: SituacaoDeAprovacao) -> None:
        if not aprovacao_permite(self.approval_status, destino):
            raise TransicaoDeAprovacaoInvalidaError(
                f"Não é possível mudar a aprovação de {self.approval_status} para {destino}."
            )

    def _transicionar(self, destino: StatusDaProposta) -> None:
        if not permite(self.status, destino):
            raise TransicaoDeStatusInvalidaError(
                f"Não é possível mudar a proposta de {self.status} para {destino}."
            )
        self.status = destino

    def _exigir_ativa(self) -> None:
        if self.status is StatusDaProposta.CANCELLED:
            raise PropostaCanceladaError("A proposta está cancelada e não aceita alteração.")
