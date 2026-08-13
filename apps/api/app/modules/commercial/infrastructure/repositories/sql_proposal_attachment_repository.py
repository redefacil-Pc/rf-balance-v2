"""Persistência dos metadados de comprovante."""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commercial.infrastructure.models.proposal_attachment_model import (
    ProposalAttachmentModel,
)


class SqlProposalAttachmentRepository:
    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def adicionar(
        self,
        *,
        proposal_id: int,
        file_name: str,
        content_type: str,
        size_bytes: int,
        storage_key: str,
        sha256: str,
        ator: int | None,
    ) -> ProposalAttachmentModel:
        modelo = ProposalAttachmentModel(
            proposal_id=proposal_id,
            file_name=file_name,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_key=storage_key,
            sha256=sha256,
            uploaded_by=ator,
        )
        self._session.add(modelo)
        await self._session.flush()
        return modelo

    async def listar(self, proposal_id: int) -> list[ProposalAttachmentModel]:
        consulta = (
            select(ProposalAttachmentModel)
            .where(ProposalAttachmentModel.proposal_id == proposal_id)
            .order_by(ProposalAttachmentModel.uploaded_at, ProposalAttachmentModel.id)
        )
        return list((await self._session.scalars(consulta)).all())

    async def obter(
        self, *, proposal_id: int, attachment_id: int
    ) -> ProposalAttachmentModel | None:
        encontrado: ProposalAttachmentModel | None = await self._session.scalar(
            select(ProposalAttachmentModel).where(
                ProposalAttachmentModel.id == attachment_id,
                # o escopo pela proposta impede baixar anexo alheio trocando o id
                ProposalAttachmentModel.proposal_id == proposal_id,
            )
        )
        return encontrado

    async def contar(self, proposal_id: int) -> int:
        total = await self._session.scalar(
            select(func.count())
            .select_from(ProposalAttachmentModel)
            .where(ProposalAttachmentModel.proposal_id == proposal_id)
        )
        return int(total or 0)

    async def remover(self, attachment_id: int) -> None:
        await self._session.execute(
            delete(ProposalAttachmentModel).where(ProposalAttachmentModel.id == attachment_id)
        )
