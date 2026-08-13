"""Tabela `sessions` — sessões ativas, com revogação e rotação (ADR-0003).

Guarda apenas o hash do token. `revoked_at` preenchido encerra a sessão
imediatamente, o que é o requisito de revogação da seção 13.1.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA
from app.platform.db.types.utc_datetime import UtcDateTime


class SessionModel(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        # caminho de acesso do request autenticado: hash -> sessão viva
        Index("ix_sessions_token_hash_expires_at", "token_hash", "expires_at"),
        Index("ix_sessions_user_id_revoked_at", "user_id", "revoked_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, server_default=AGORA
    )
    rotated_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(60), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(32), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
