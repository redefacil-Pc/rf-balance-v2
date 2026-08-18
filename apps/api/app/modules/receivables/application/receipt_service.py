from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.commercial.application.ports.attachment_storage import AttachmentStorage
from app.modules.commercial.domain.entities.proposal import Proposal
from app.modules.commercial.domain.policies import settlement_tolerance_policy as tolerancia
from app.modules.commercial.domain.value_objects.situacao_de_aprovacao import SituacaoDeAprovacao
from app.modules.commercial.domain.value_objects.status_da_proposta import StatusDaProposta
from app.modules.commercial.infrastructure.models.proposal_model import ProposalModel
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    SqlProposalRepository,
)
from app.modules.commissions.application.standard_commission_engine import (
    StandardCommissionEngine,
)
from app.modules.identity.infrastructure.models.user_model import UserModel
from app.modules.organization.infrastructure.models.receiving_account_model import (
    ReceivingAccountModel,
)
from app.modules.receivables.application.ports.receiving_account_directory import (
    ReceivingAccountDirectory,
)
from app.modules.receivables.domain.errors import (
    AutoAprovacaoDeRecebimentoError,
    ChaveIdempotenteEmConflitoError,
    FluxoDeRecebimentoInvalidoError,
    RecebimentoInvalidoError,
    RecebimentoNaoEncontradoError,
)
from app.modules.receivables.infrastructure.models.receipt_model import (
    ReceiptModel,
    ReceiptReversalModel,
)
from app.modules.receivables.infrastructure.recognizers.sql_receipt_recognizer import (
    DECLARADO,
    RECONHECIDO,
    SqlReceiptRecognizer,
)
from app.platform.bus.outbox_recorder import SqlOutboxRecorder
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import Clock
from app.shared.domain.dinheiro import Dinheiro

TIPOS_ACEITOS = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}
TAMANHO_MAXIMO = 10 * 1024 * 1024


def _motivo_da_recusa(proposal: Proposal) -> str:
    """Diz **por que** não cabe recebimento agora — a mensagem genérica manda o
    operador adivinhar se deve esperar a decisão ou se não há mais o que pagar."""
    if proposal.approval_status is SituacaoDeAprovacao.SUBMITTED:
        return (
            "A proposta está aguardando a conferência do financeiro e não aceita "
            "novo recebimento. Aguarde a decisão."
        )
    if proposal.status is StatusDaProposta.PAID:
        return "A proposta já está quitada e não tem saldo a receber."
    return "A proposta não aceita recebimento no estado atual."


@dataclass(frozen=True, slots=True)
class ReceiptResult:
    receipt: ReceiptModel
    proposal_status: str
    proposal_paid_amount: Decimal
    proposal_outstanding_amount: Decimal


@dataclass(frozen=True, slots=True)
class ReceiptListItem:
    receipt: ReceiptModel
    customer_name: str
    creator_name: str
    proposal_approval_status: str
    reversal_reason: str | None
    reversed_amount: Decimal
    receiving_account_label: str


class ReceiptService:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        proposals: SqlProposalRepository,
        storage: AttachmentStorage,
        audit: AuditRecorder,
        outbox: SqlOutboxRecorder,
        commissions: StandardCommissionEngine,
        contas: ReceivingAccountDirectory,
        clock: Clock,
        timezone: str,
    ) -> None:
        self._contas = contas
        self._uow = uow
        self._session: AsyncSession = uow.session
        self._proposals = proposals
        self._storage = storage
        self._audit = audit
        self._outbox = outbox
        self._commissions = commissions
        self._clock = clock
        self._timezone = ZoneInfo(timezone)

    async def create(
        self,
        *,
        proposal_id: int,
        amount: Decimal,
        business_date: date,
        payment_time: time | None,
        payment_method: str,
        receiving_account_id: int,
        reference: str | None,
        notes: str | None,
        file_name: str,
        content_type: str,
        content: bytes,
        idempotency_key: str,
        actor: int,
        correlation_id: str | None,
    ) -> ReceiptResult:
        self._validate_proof(content_type, content)
        request_hash = hashlib.sha256(
            f"{proposal_id}|{amount}|{business_date}|{payment_time}|{payment_method}"
            f"|{receiving_account_id}|{reference}|{notes}|".encode()
            + hashlib.sha256(content).digest()
        ).hexdigest()
        existing = await self._session.scalar(
            select(ReceiptModel).where(
                ReceiptModel.created_by == actor, ReceiptModel.idempotency_key == idempotency_key
            )
        )
        if existing is not None:
            if existing.request_hash != request_hash:
                raise ChaveIdempotenteEmConflitoError(
                    "Esta chave já foi usada em outro lançamento. Gere uma nova chave."
                )
            return await self._result(existing)

        proposal = await self._proposals.obter_para_atualizacao(proposal_id)
        if proposal is None:
            raise RecebimentoInvalidoError(f"Proposta {proposal_id} não encontrada.")
        if proposal.status is StatusDaProposta.CANCELLED:
            raise FluxoDeRecebimentoInvalidoError("A proposta está cancelada.")
        if not proposal.aceita_recebimento:
            raise FluxoDeRecebimentoInvalidoError(_motivo_da_recusa(proposal))

        if not await self._contas.esta_disponivel(receiving_account_id):
            raise RecebimentoInvalidoError("Selecione uma conta de recebimento ativa.")

        payment_datetime = self._validate_payment_datetime(business_date, payment_time)
        reconhecedor = SqlReceiptRecognizer(self._session, self._clock.now())
        ja_declarado = await reconhecedor.total_declarado(proposal_id)
        limite = (
            proposal.company_commission_amount
            + tolerancia.resolver(proposal.tolerance_policy_version).excedente_tolerado
        )
        if ja_declarado + Dinheiro.de(amount) > limite:
            raise RecebimentoInvalidoError(
                "O valor ultrapassa o saldo da proposta e a tolerância de sobrepagamento."
            )

        extension = TIPOS_ACEITOS[content_type]
        storage_key = f"receipts/{proposal_id}/{uuid.uuid4().hex}{extension}"
        await self._storage.guardar(chave=storage_key, conteudo=content, content_type=content_type)
        receipt = ReceiptModel(
            proposal_id=proposal_id,
            amount=Dinheiro.de(amount).valor,
            business_date=business_date,
            payment_datetime=payment_datetime,
            payment_method=payment_method.strip().upper(),
            receiving_account_id=receiving_account_id,
            reference=reference.strip()[:100] if reference else None,
            notes=notes.strip()[:255] if notes else None,
            status="SUBMITTED",
            proof_file_name=(file_name.strip() or "comprovante")[:255],
            proof_content_type=content_type,
            proof_size_bytes=len(content),
            proof_storage_key=storage_key,
            proof_sha256=hashlib.sha256(content).hexdigest(),
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            created_by=actor,
        )
        self._session.add(receipt)
        await self._session.flush()
        self._audit.registrar(
            module="receivables",
            action="receipt.submitted",
            actor_user_id=actor,
            aggregate_type="receipt",
            aggregate_id=str(receipt.id),
            correlation_id=correlation_id,
            payload={
                "proposal_id": proposal_id,
                "amount": str(receipt.amount),
                "proof_sha256": receipt.proof_sha256,
            },
        )
        self._outbox.registrar(
            event_type="receivable.receipt_submitted.v1",
            aggregate_type="receipt",
            aggregate_id=str(receipt.id),
            correlation_id=correlation_id,
            payload={
                "proposal_id": proposal_id,
                "amount": str(receipt.amount),
                "business_date": receipt.business_date.isoformat(),
            },
        )
        await self._uow.commit()
        return ReceiptResult(
            receipt,
            proposal.status.value,
            proposal.paid_amount.valor,
            proposal.outstanding_amount.valor,
        )

    async def decide(
        self,
        *,
        receipt_id: int,
        approve: bool,
        reason: str | None,
        actor: int,
        correlation_id: str | None,
    ) -> ReceiptResult:
        """Conferência avulsa do Financeiro, para pagamento posterior.

        Só existe para o que chega **depois** da proposta aprovada: aquela
        aprovação já aconteceu e é terminal, então não há como ela reconhecer um
        valor que ainda nem tinha sido pago. O que foi declarado antes do envio
        é conferido junto da decisão da proposta, e não passa por aqui.
        """
        receipt = await self._locked(receipt_id)
        if receipt.status != DECLARADO:
            raise FluxoDeRecebimentoInvalidoError("Este recebimento já foi conferido.")

        proposal = await self._proposals.obter(receipt.proposal_id)
        if proposal is None or proposal.approval_status is not SituacaoDeAprovacao.APPROVED:
            raise FluxoDeRecebimentoInvalidoError(
                "Este recebimento será conferido junto da aprovação da proposta."
            )
        if receipt.created_by == actor:
            raise AutoAprovacaoDeRecebimentoError(
                "Quem declarou o recebimento não pode conferir o próprio lançamento."
            )
        if not approve and len((reason or "").strip()) < 3:
            raise RecebimentoInvalidoError("Informe o motivo da devolução.")

        receipt.status = RECONHECIDO if approve else "REJECTED"
        receipt.rejection_reason = None if approve else (reason or "").strip()
        receipt.decided_at = self._clock.now()
        receipt.decided_by = actor
        # a soma do recálculo precisa enxergar a decisão na própria transação;
        # a fábrica de sessões desabilita o autoflush
        await self._session.flush()
        atualizada = await self._recalculate(receipt.proposal_id)
        if approve:
            await self._commissions.gerar_para_proposta(
                receipt.proposal_id, correlation_id=correlation_id
            )

        self._audit.registrar(
            module="receivables",
            action="receipt.approved" if approve else "receipt.rejected",
            actor_user_id=actor,
            aggregate_type="receipt",
            aggregate_id=str(receipt.id),
            correlation_id=correlation_id,
            payload={"reason": receipt.rejection_reason, "amount": str(receipt.amount)},
        )
        self._outbox.registrar(
            event_type=(
                "receivable.receipt_confirmed.v1" if approve else "receivable.receipt_rejected.v1"
            ),
            aggregate_type="receipt",
            aggregate_id=str(receipt.id),
            correlation_id=correlation_id,
            payload={
                "proposal_id": receipt.proposal_id,
                "amount": str(receipt.amount),
                "business_date": receipt.business_date.isoformat(),
            },
        )
        await self._uow.commit()
        return ReceiptResult(
            receipt,
            atualizada.status.value,
            atualizada.paid_amount.valor,
            atualizada.outstanding_amount.valor,
        )

    async def remove(self, *, receipt_id: int, actor: int, correlation_id: str | None) -> None:
        """Remove um recebimento ainda não conferido.

        Existe porque a Finalização digita antes de enviar e erra: valor trocado,
        comprovante errado. Depois do envio não remove — o conjunto que o
        Financeiro analisa não muda por baixo da decisão.
        """
        receipt = await self._locked(receipt_id)
        if receipt.status != DECLARADO:
            raise FluxoDeRecebimentoInvalidoError(
                "Este recebimento já foi conferido. Use o estorno."
            )
        proposal = await self._proposals.obter(receipt.proposal_id)
        # a mesma janela que permite declarar permite corrigir: o que não pode é
        # sumir com um lançamento enquanto o Financeiro o analisa
        if proposal is None or not proposal.aceita_recebimento:
            raise FluxoDeRecebimentoInvalidoError(
                "A proposta está em análise e o recebimento não pode ser removido agora."
            )

        chave = receipt.proof_storage_key
        await self._session.delete(receipt)
        self._audit.registrar(
            module="receivables",
            action="receipt.removed",
            actor_user_id=actor,
            aggregate_type="receipt",
            aggregate_id=str(receipt_id),
            correlation_id=correlation_id,
            payload={"proposal_id": receipt.proposal_id, "amount": str(receipt.amount)},
        )
        self._outbox.registrar(
            event_type="receivable.receipt_removed.v1",
            aggregate_type="receipt",
            aggregate_id=str(receipt_id),
            correlation_id=correlation_id,
            payload={"proposal_id": receipt.proposal_id, "amount": str(receipt.amount)},
        )
        await self._uow.commit()
        # commit primeiro: objeto órfão no bucket é inofensivo, linha apontando
        # para arquivo inexistente não é
        await self._storage.remover(chave)

    async def reverse(
        self,
        *,
        receipt_id: int,
        reason: str,
        business_date: date,
        amount: Decimal | None,
        actor: int,
        correlation_id: str | None,
    ) -> ReceiptResult:
        receipt = await self._locked(receipt_id)
        if receipt.status != RECONHECIDO:
            raise FluxoDeRecebimentoInvalidoError(
                "Somente recebimento já reconhecido pode ser estornado."
            )
        self._validate_business_date(business_date)
        total_estornado = Decimal(
            await self._session.scalar(
                select(func.coalesce(func.sum(ReceiptReversalModel.amount), 0)).where(
                    ReceiptReversalModel.receipt_id == receipt_id
                )
            )
            or 0
        )
        restante = Dinheiro.de(receipt.amount - total_estornado)
        valor_do_estorno = restante if amount is None else Dinheiro.de(amount)
        if not valor_do_estorno.positivo or valor_do_estorno > restante:
            raise FluxoDeRecebimentoInvalidoError(
                "O estorno não pode exceder o valor ainda não estornado do recebimento."
            )
        reversal = ReceiptReversalModel(
            receipt_id=receipt.id,
            proposal_id=receipt.proposal_id,
            amount=valor_do_estorno.valor,
            reason=reason.strip(),
            business_date=business_date,
            created_by=actor,
        )
        self._session.add(reversal)
        await self._session.flush()
        proposal = await self._recalculate(receipt.proposal_id)
        await self._commissions.estornar(reversal.id, correlation_id=correlation_id)
        self._audit.registrar(
            module="receivables",
            action="receipt.reversed",
            actor_user_id=actor,
            aggregate_type="receipt",
            aggregate_id=str(receipt.id),
            correlation_id=correlation_id,
            payload={
                "reversal_id": reversal.id,
                "reason": reversal.reason,
                "amount": str(reversal.amount),
            },
        )
        self._outbox.registrar(
            event_type="receivable.receipt_reversed.v1",
            aggregate_type="receipt_reversal",
            aggregate_id=str(reversal.id),
            correlation_id=correlation_id,
            payload={
                "receipt_id": receipt.id,
                "proposal_id": receipt.proposal_id,
                "amount": str(reversal.amount),
                "business_date": reversal.business_date.isoformat(),
            },
        )
        await self._uow.commit()
        return ReceiptResult(
            receipt,
            proposal.status.value,
            proposal.paid_amount.valor,
            proposal.outstanding_amount.valor,
        )

    async def list(
        self, *, status: str | None = None, proposal_id: int | None = None
    ) -> list[ReceiptListItem]:
        ultimo_motivo_de_estorno = (
            select(ReceiptReversalModel.reason)
            .where(ReceiptReversalModel.receipt_id == ReceiptModel.id)
            .order_by(ReceiptReversalModel.created_at.desc(), ReceiptReversalModel.id.desc())
            .limit(1)
            .scalar_subquery()
        )
        valor_estornado = (
            select(func.coalesce(func.sum(ReceiptReversalModel.amount), 0))
            .where(ReceiptReversalModel.receipt_id == ReceiptModel.id)
            .scalar_subquery()
        )
        query = (
            select(
                ReceiptModel,
                ProposalModel.customer_name,
                UserModel.full_name,
                ProposalModel.approval_status,
                ultimo_motivo_de_estorno,
                valor_estornado,
                ReceivingAccountModel.label,
            )
            .join(ProposalModel, ProposalModel.id == ReceiptModel.proposal_id)
            .join(UserModel, UserModel.id == ReceiptModel.created_by)
            .join(
                ReceivingAccountModel,
                ReceivingAccountModel.id == ReceiptModel.receiving_account_id,
            )
        )
        if status:
            query = query.where(ReceiptModel.status == status)
        if proposal_id:
            query = query.where(ReceiptModel.proposal_id == proposal_id)
        rows = (
            await self._session.execute(query.order_by(ReceiptModel.created_at.desc()).limit(200))
        ).all()
        return [
            ReceiptListItem(
                receipt=row[0],
                customer_name=str(row[1]),
                creator_name=str(row[2]),
                proposal_approval_status=str(row[3]),
                reversal_reason=row[4],
                reversed_amount=Decimal(row[5]),
                receiving_account_label=str(row[6]),
            )
            for row in rows
        ]

    async def get(self, receipt_id: int) -> ReceiptModel:
        receipt = await self._session.get(ReceiptModel, receipt_id)
        if receipt is None:
            raise RecebimentoNaoEncontradoError(f"Recebimento {receipt_id} não encontrado.")
        return receipt

    async def _locked(self, receipt_id: int) -> ReceiptModel:
        receipt = await self._session.scalar(
            select(ReceiptModel).where(ReceiptModel.id == receipt_id).with_for_update()
        )
        if receipt is None:
            raise RecebimentoNaoEncontradoError(f"Recebimento {receipt_id} não encontrado.")
        return receipt

    async def _recalculate(self, proposal_id: int) -> Proposal:
        proposal = await self._proposals.obter_para_atualizacao(proposal_id)
        if proposal is None:
            raise RecebimentoInvalidoError(f"Proposta {proposal_id} não encontrada.")
        # mesma conta usada no reconhecimento da aprovação: uma definição só de
        # "quanto está reconhecido", para os dois caminhos não divergirem
        total = await SqlReceiptRecognizer(self._session, self._clock.now()).total(proposal_id)
        proposal.registrar_total_recebido(total)
        await self._proposals.salvar(
            proposal, versao_do_cliente=proposal.version, quando=self._clock.now(), ator=None
        )
        return proposal

    async def _result(self, receipt: ReceiptModel) -> ReceiptResult:
        proposal = await self._proposals.obter(receipt.proposal_id)
        assert proposal is not None
        return ReceiptResult(
            receipt,
            proposal.status.value,
            proposal.paid_amount.valor,
            proposal.outstanding_amount.valor,
        )

    @staticmethod
    def _validate_proof(content_type: str, content: bytes) -> None:
        if content_type not in TIPOS_ACEITOS:
            raise RecebimentoInvalidoError("Envie um comprovante PDF, JPG ou PNG.")
        if not content:
            raise RecebimentoInvalidoError("O comprovante está vazio.")
        if len(content) > TAMANHO_MAXIMO:
            raise RecebimentoInvalidoError("O comprovante ultrapassa 10 MB.")

    def _validate_business_date(self, business_date: date) -> None:
        if business_date > self._clock.business_date():
            raise RecebimentoInvalidoError("A data do recebimento não pode estar no futuro.")

    def _validate_payment_datetime(
        self, business_date: date, payment_time: time | None
    ) -> datetime | None:
        self._validate_business_date(business_date)
        if payment_time is None:
            return None
        instante = datetime.combine(business_date, payment_time, tzinfo=self._timezone).astimezone(
            UTC
        )
        if instante > self._clock.now():
            raise RecebimentoInvalidoError(
                "A data e hora do recebimento não podem estar no futuro."
            )
        return instante
