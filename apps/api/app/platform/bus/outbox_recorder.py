"""Registra eventos transacionais na outbox.

O recorder apenas adiciona a linha à sessão recebida. O commit continua sendo
responsabilidade do caso de uso, garantindo que negócio, auditoria e evento
sejam confirmados ou revertidos juntos.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.bus.outbox_model import OutboxEventModel
from app.platform.time.clock import Clock


class SqlOutboxRecorder:
    __slots__ = ("_clock", "_session")

    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def registrar(
        self,
        *,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None:
        agora = self._clock.now()
        self._session.add(
            OutboxEventModel(
                occurred_at=agora,
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                correlation_id=correlation_id,
                payload=payload,
                available_at=agora,
            )
        )
