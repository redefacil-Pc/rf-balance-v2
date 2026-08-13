"""Persistência de sessão em MySQL."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.domain.entities.session import Session
from app.modules.identity.infrastructure.models.session_model import SessionModel


class SqlSessionRepository:
    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def criar(
        self,
        *,
        user_id: int,
        token_hash: str,
        csrf_token: str,
        emitida_em: datetime,
        expira_em: datetime,
        ip_hash: str | None,
        user_agent: str | None,
    ) -> Session:
        modelo = SessionModel(
            user_id=user_id,
            token_hash=token_hash,
            csrf_token=csrf_token,
            issued_at=emitida_em,
            expires_at=expira_em,
            last_used_at=emitida_em,
            ip_hash=ip_hash,
            user_agent=user_agent,
        )
        self._session.add(modelo)
        await self._session.flush()
        return self._para_entidade(modelo)

    async def buscar_por_token_hash(self, token_hash: str) -> Session | None:
        modelo = await self._session.scalar(
            select(SessionModel).where(SessionModel.token_hash == token_hash)
        )
        return self._para_entidade(modelo) if modelo else None

    async def rotacionar(self, *, session_id: int, novo_token_hash: str, quando: datetime) -> None:
        await self._session.execute(
            update(SessionModel)
            .where(SessionModel.id == session_id)
            .values(token_hash=novo_token_hash, rotated_at=quando, last_used_at=quando)
        )

    async def marcar_uso(self, *, session_id: int, quando: datetime) -> None:
        await self._session.execute(
            update(SessionModel).where(SessionModel.id == session_id).values(last_used_at=quando)
        )

    async def revogar(self, *, session_id: int, quando: datetime, motivo: str) -> None:
        await self._session.execute(
            update(SessionModel)
            .where(SessionModel.id == session_id, SessionModel.revoked_at.is_(None))
            .values(revoked_at=quando, revoked_reason=motivo)
        )

    async def token_hashes_vivos(self, user_id: int) -> list[str]:
        """Chaves de cache das sessões ainda válidas do usuário.

        Revogar no banco não basta: a resolução de sessão consulta o Redis
        antes, e serviria o usuário antigo — com os papéis antigos e ativo — até
        o TTL vencer. Quem desativa conta ou troca papel precisa derrubar estas
        chaves junto, no mesmo fluxo.
        """
        encontrados = await self._session.scalars(
            select(SessionModel.token_hash).where(
                SessionModel.user_id == user_id, SessionModel.revoked_at.is_(None)
            )
        )
        return [str(t) for t in encontrados.all()]

    async def revogar_do_usuario(self, *, user_id: int, quando: datetime, motivo: str) -> int:
        """Revoga todas as sessões vivas do usuário. Usado em troca de senha e
        desativação de conta; retorna quantas foram encerradas, para auditoria."""
        resultado = cast(
            "CursorResult[Any]",
            await self._session.execute(
                update(SessionModel)
                .where(SessionModel.user_id == user_id, SessionModel.revoked_at.is_(None))
                .values(revoked_at=quando, revoked_reason=motivo)
            ),
        )
        return resultado.rowcount or 0

    @staticmethod
    def _para_entidade(modelo: SessionModel) -> Session:
        return Session(
            id=modelo.id,
            user_id=modelo.user_id,
            token_hash=modelo.token_hash,
            csrf_token=modelo.csrf_token,
            issued_at=modelo.issued_at,
            expires_at=modelo.expires_at,
            last_used_at=modelo.last_used_at,
            rotated_at=modelo.rotated_at,
            revoked_at=modelo.revoked_at,
            revoked_reason=modelo.revoked_reason,
        )
