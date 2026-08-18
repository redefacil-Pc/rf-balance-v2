"""Implementação da porta `ReceivingAccountDirectory`.

Mora em `organization` porque é o módulo dono da tabela: quem responde sobre a
conta é quem a administra.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organization.infrastructure.models.receiving_account_model import (
    ReceivingAccountModel,
)


class SqlReceivingAccountDirectory:
    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def esta_disponivel(self, account_id: int) -> bool:
        encontrada = await self._session.scalar(
            select(ReceivingAccountModel.id).where(
                ReceivingAccountModel.id == account_id,
                ReceivingAccountModel.is_active.is_(True),
            )
        )
        return encontrada is not None
