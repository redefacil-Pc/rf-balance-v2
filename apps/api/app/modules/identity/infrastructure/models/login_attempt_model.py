"""Tabela `login_attempts` — rate limit e investigação (seção 13.1).

Guarda o e-mail tentado e o hash do IP, nunca a senha nem o IP em claro.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA
from app.platform.db.types.utc_datetime import UtcDateTime


class LoginAttemptModel(Base):
    __tablename__ = "login_attempts"
    __table_args__ = (
        # caminho de acesso da checagem de throttle
        Index("ix_login_attempts_email_attempted_at", "email", "attempted_at"),
        Index("ix_login_attempts_ip_hash_attempted_at", "ip_hash", "attempted_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String(32), nullable=True)
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(60), nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, server_default=AGORA
    )
