"""Tabela `outbox_events` — entrega confiável de eventos (seção 6.8).

O evento é gravado na mesma transação do negócio; o dispatcher publica depois e
marca como processado. Nunca publicar dentro da transação.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA
from app.platform.db.types.utc_datetime import UtcDateTime


class OutboxEventModel(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        # caminho de acesso do dispatcher: pendentes já disponíveis, em ordem
        Index("ix_outbox_events_processed_at_available_at", "processed_at", "available_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    aggregate_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    available_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, server_default=AGORA
    )
    processed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
