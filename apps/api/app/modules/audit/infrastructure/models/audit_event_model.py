"""Tabela `audit_events` — trilha append-only (seção 7.16).

Nunca sofre UPDATE nem DELETE. Correção é evento novo.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA
from app.platform.db.types.utc_datetime import UtcDateTime


class AuditEventModel(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_aggregate", "aggregate_type", "aggregate_id"),
        Index("ix_audit_events_actor_occurred_at", "actor_user_id", "occurred_at"),
        Index("ix_audit_events_correlation_id", "correlation_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    # data operacional em America/Sao_Paulo, distinta de occurred_at
    business_date: Mapped[date] = mapped_column(Date, nullable=False)
    module: Mapped[str] = mapped_column(String(40), nullable=False)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    actor_label: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    aggregate_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    aggregate_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # payload sem PII crua e sem segredo
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
