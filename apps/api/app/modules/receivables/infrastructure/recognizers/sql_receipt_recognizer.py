"""Reconhecimento dos recebimentos declarados, no commit da aprovação.

Implementa a porta que `commercial` declara. Fica em `receivables` porque é aqui
que se sabe o que é um recebimento e o que um estorno faz com ele.

Reconhecer é marcar como `APPROVED` o que a Finalização declarou e o Financeiro
acabou de conferir. O total devolvido **desconta o estornado**: dinheiro que
voltou pelo banco não é dinheiro recebido.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Subquery

from app.modules.receivables.infrastructure.models.receipt_model import (
    ReceiptModel,
    ReceiptReversalModel,
)
from app.shared.domain.dinheiro import Dinheiro

#: recebimento declarado pela Finalização, à espera da conferência do Financeiro
DECLARADO = "SUBMITTED"
#: conferido no extrato e reconhecido junto da aprovação da proposta
RECONHECIDO = "APPROVED"


class SqlReceiptRecognizer:
    __slots__ = ("_agora", "_session")

    def __init__(self, session: AsyncSession, agora: datetime) -> None:
        self._session = session
        self._agora = agora

    async def contar_declarados(self, proposal_id: int) -> int:
        total = await self._session.scalar(
            select(func.count(ReceiptModel.id)).where(
                ReceiptModel.proposal_id == proposal_id,
                ReceiptModel.status == DECLARADO,
            )
        )
        return int(total or 0)

    async def reconhecer(self, proposal_id: int, *, ator: int | None) -> Dinheiro:
        await self._session.execute(
            update(ReceiptModel)
            .where(
                ReceiptModel.proposal_id == proposal_id,
                ReceiptModel.status == DECLARADO,
            )
            .values(status=RECONHECIDO, decided_at=self._agora, decided_by=ator)
        )
        # a soma abaixo precisa enxergar a atualização acima na própria
        # transação; a fábrica de sessões desabilita o autoflush
        await self._session.flush()
        return await self.total(proposal_id)

    async def foi_declarado_por(self, proposal_id: int, actor: int) -> bool:
        receipt_id = await self._session.scalar(
            select(ReceiptModel.id).where(
                ReceiptModel.proposal_id == proposal_id,
                ReceiptModel.created_by == actor,
                ReceiptModel.status == DECLARADO,
            )
        )
        return receipt_id is not None

    async def total(self, proposal_id: int) -> Dinheiro:
        """Total reconhecido e não estornado."""
        estornado = self._estornado_por_recebimento()
        soma = await self._session.scalar(
            select(
                func.coalesce(
                    func.sum(ReceiptModel.amount - func.coalesce(estornado.c.amount, 0)), 0
                )
            )
            .outerjoin(estornado, estornado.c.receipt_id == ReceiptModel.id)
            .where(
                ReceiptModel.proposal_id == proposal_id,
                ReceiptModel.status == RECONHECIDO,
            )
        )
        return Dinheiro.de(Decimal(soma or 0))

    async def total_declarado(self, proposal_id: int) -> Dinheiro:
        """Total reconhecível, inclusive o que ainda aguarda conferência."""
        estornado = self._estornado_por_recebimento()
        soma = await self._session.scalar(
            select(
                func.coalesce(
                    func.sum(ReceiptModel.amount - func.coalesce(estornado.c.amount, 0)), 0
                )
            )
            .outerjoin(estornado, estornado.c.receipt_id == ReceiptModel.id)
            .where(
                ReceiptModel.proposal_id == proposal_id,
                ReceiptModel.status.in_((DECLARADO, RECONHECIDO)),
            )
        )
        return Dinheiro.de(Decimal(soma or 0))

    @staticmethod
    def _estornado_por_recebimento() -> Subquery:
        return (
            select(
                ReceiptReversalModel.receipt_id.label("receipt_id"),
                func.sum(ReceiptReversalModel.amount).label("amount"),
            )
            .group_by(ReceiptReversalModel.receipt_id)
            .subquery()
        )
