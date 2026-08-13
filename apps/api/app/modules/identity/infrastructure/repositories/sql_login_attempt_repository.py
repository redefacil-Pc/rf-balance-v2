"""Persistência e contagem de tentativas de login."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.infrastructure.models.login_attempt_model import LoginAttemptModel


class SqlLoginAttemptRepository:
    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def registrar(
        self,
        *,
        email: str,
        ip_hash: str | None,
        sucesso: bool,
        motivo: str | None,
        quando: datetime,
    ) -> None:
        self._session.add(
            LoginAttemptModel(
                email=email,
                ip_hash=ip_hash,
                succeeded=sucesso,
                reason=motivo,
                attempted_at=quando,
            )
        )

    async def contar_falhas(self, *, email: str, ip_hash: str | None, desde: datetime) -> int:
        criterio = (
            or_(LoginAttemptModel.email == email, LoginAttemptModel.ip_hash == ip_hash)
            if ip_hash
            else LoginAttemptModel.email == email
        )
        total = await self._session.scalar(
            select(func.count())
            .select_from(LoginAttemptModel)
            .where(
                LoginAttemptModel.succeeded.is_(False),
                LoginAttemptModel.attempted_at >= desde,
                criterio,
            )
        )
        return int(total or 0)
