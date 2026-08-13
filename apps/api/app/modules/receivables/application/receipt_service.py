from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.commercial.application.ports.attachment_storage import AttachmentStorage
from app.modules.commercial.domain.entities.proposal import Proposal
from app.modules.commercial.domain.value_objects.situacao_de_aprovacao import SituacaoDeAprovacao
from app.modules.commercial.domain.value_objects.status_da_proposta import StatusDaProposta
from app.modules.commercial.infrastructure.models.proposal_model import ProposalModel
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    SqlProposalRepository,
)
from app.modules.identity.infrastructure.models.user_model import UserModel
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
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import Clock
from app.shared.domain.dinheiro import Dinheiro

TIPOS_ACEITOS = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}
TAMANHO_MAXIMO = 10 * 1024 * 1024


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
    reversal_reason: str | None


class ReceiptService:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        proposals: SqlProposalRepository,
        storage: AttachmentStorage,
        audit: AuditRecorder,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._session: AsyncSession = uow.session
        self._proposals = proposals
        self._storage = storage
        self._audit = audit
        self._clock = clock

    async def create(
        self,
        *,
        proposal_id: int,
        amount: Decimal,
        business_date: date,
        payment_method: str,
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
            f"{proposal_id}|{amount}|{business_date}|{payment_method}|{reference}|{notes}|".encode()
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
        if proposal.approval_status is not SituacaoDeAprovacao.APPROVED:
            raise FluxoDeRecebimentoInvalidoError(
                "Somente propostas aprovadas podem receber lançamentos."
            )
        if proposal.status is StatusDaProposta.CANCELLED:
            raise FluxoDeRecebimentoInvalidoError("A proposta está cancelada.")

        extension = TIPOS_ACEITOS[content_type]
        storage_key = f"receipts/{proposal_id}/{uuid.uuid4().hex}{extension}"
        await self._storage.guardar(chave=storage_key, conteudo=content, content_type=content_type)
        receipt = ReceiptModel(
            proposal_id=proposal_id,
            amount=Dinheiro.de(amount).valor,
            business_date=business_date,
            payment_method=payment_method.strip().upper(),
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
        receipt = await self._locked(receipt_id)
        if receipt.status != "SUBMITTED":
            raise FluxoDeRecebimentoInvalidoError("Este recebimento já foi decidido.")
        if receipt.created_by == actor:
            raise AutoAprovacaoDeRecebimentoError(
                "Quem lançou o recebimento não pode aprovar o próprio lançamento."
            )
        if not approve and len((reason or "").strip()) < 3:
            raise RecebimentoInvalidoError("Informe o motivo da devolução.")

        receipt.status = "APPROVED" if approve else "REJECTED"
        receipt.rejection_reason = None if approve else reason.strip() if reason else None
        receipt.decided_at = self._clock.now()
        receipt.decided_by = actor
        # A fábrica desabilita autoflush: a soma abaixo precisa enxergar a
        # decisão dentro da própria transação.
        await self._session.flush()
        proposal = await self._recalculate(receipt.proposal_id)
        self._audit.registrar(
            module="receivables",
            action="receipt.approved" if approve else "receipt.rejected",
            actor_user_id=actor,
            aggregate_type="receipt",
            aggregate_id=str(receipt.id),
            correlation_id=correlation_id,
            payload={"reason": receipt.rejection_reason},
        )
        await self._uow.commit()
        return ReceiptResult(
            receipt,
            proposal.status.value,
            proposal.paid_amount.valor,
            proposal.outstanding_amount.valor,
        )

    async def reverse(
        self,
        *,
        receipt_id: int,
        reason: str,
        business_date: date,
        actor: int,
        correlation_id: str | None,
    ) -> ReceiptResult:
        receipt = await self._locked(receipt_id)
        if receipt.status != "APPROVED":
            raise FluxoDeRecebimentoInvalidoError(
                "Somente recebimento aprovado pode ser estornado."
            )
        existing = await self._session.scalar(
            select(ReceiptReversalModel).where(ReceiptReversalModel.receipt_id == receipt_id)
        )
        if existing is not None:
            raise FluxoDeRecebimentoInvalidoError("Este recebimento já foi estornado.")
        reversal = ReceiptReversalModel(
            receipt_id=receipt.id,
            proposal_id=receipt.proposal_id,
            amount=receipt.amount,
            reason=reason.strip(),
            business_date=business_date,
            created_by=actor,
        )
        self._session.add(reversal)
        await self._session.flush()
        proposal = await self._recalculate(receipt.proposal_id)
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
        query = (
            select(
                ReceiptModel,
                ProposalModel.customer_name,
                UserModel.full_name,
                ReceiptReversalModel.reason,
            )
            .join(ProposalModel, ProposalModel.id == ReceiptModel.proposal_id)
            .join(UserModel, UserModel.id == ReceiptModel.created_by)
            .outerjoin(ReceiptReversalModel, ReceiptReversalModel.receipt_id == ReceiptModel.id)
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
                reversal_reason=row[3],
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
        total = await self._session.scalar(
            select(func.coalesce(func.sum(ReceiptModel.amount), 0))
            .outerjoin(ReceiptReversalModel, ReceiptReversalModel.receipt_id == ReceiptModel.id)
            .where(
                ReceiptModel.proposal_id == proposal_id,
                ReceiptModel.status == "APPROVED",
                ReceiptReversalModel.id.is_(None),
            )
        )
        proposal.registrar_total_recebido(Dinheiro.de(Decimal(total or 0)))
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
