"""Publica a outbox no Redis Streams com entrega ao menos uma vez."""

from __future__ import annotations

import json
from datetime import timedelta

from redis.asyncio import Redis
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.bus.outbox_model import OutboxEventModel
from app.platform.time.clock import Clock

STREAM_DE_EVENTOS = "rfbalance:domain-events"


class OutboxDispatcher:
    __slots__ = ("_clock", "_maxlen", "_redis", "_session", "_stream")

    def __init__(
        self,
        *,
        session: AsyncSession,
        redis: Redis,
        clock: Clock,
        stream: str = STREAM_DE_EVENTOS,
        maxlen: int = 10_000,
    ) -> None:
        self._session = session
        self._redis = redis
        self._clock = clock
        self._stream = stream
        self._maxlen = maxlen

    async def despachar_lote(self, limite: int = 100) -> int:
        agora = self._clock.now()
        eventos = list(
            (
                await self._session.scalars(
                    select(OutboxEventModel)
                    .where(
                        OutboxEventModel.processed_at.is_(None),
                        or_(
                            OutboxEventModel.available_at.is_(None),
                            OutboxEventModel.available_at <= agora,
                        ),
                    )
                    .order_by(OutboxEventModel.id)
                    .limit(limite)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for evento in eventos:
            try:
                await self._redis.xadd(
                    self._stream,
                    {
                        "outbox_id": str(evento.id),
                        "event_type": evento.event_type,
                        "aggregate_type": evento.aggregate_type or "",
                        "aggregate_id": evento.aggregate_id or "",
                        "correlation_id": evento.correlation_id or "",
                        "occurred_at": evento.occurred_at.isoformat(),
                        "payload": json.dumps(
                            evento.payload, ensure_ascii=False, separators=(",", ":")
                        ),
                    },
                    maxlen=self._maxlen,
                    approximate=True,
                )
                evento.processed_at = agora
                evento.attempts += 1
                evento.last_error = None
            except Exception as exc:
                evento.attempts += 1
                evento.last_error = str(exc)[:2000]
                atraso = min(2 ** min(evento.attempts, 8), 300)
                evento.available_at = agora + timedelta(seconds=atraso)

        await self._session.commit()
        return len(eventos)
