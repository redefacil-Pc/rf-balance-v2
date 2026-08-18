from __future__ import annotations

import pytest
from sqlalchemy import select

from app.platform.bus.outbox_dispatcher import STREAM_DE_EVENTOS, OutboxDispatcher
from app.platform.bus.outbox_model import OutboxEventModel
from app.platform.cache.redis_client import criar_cliente
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes
from app.platform.time.clock import SystemClock

pytestmark = pytest.mark.integration


async def test_dispatcher_publica_no_stream_e_marca_processado() -> None:
    settings = get_settings()
    engine = criar_engine(settings.database)
    redis = criar_cliente(settings.redis)
    sessoes = criar_fabrica_de_sessoes(engine)
    await redis.delete(STREAM_DE_EVENTOS)
    try:
        async with sessoes() as session:
            evento = OutboxEventModel(
                event_type="test.event.v1",
                aggregate_type="test",
                aggregate_id="1",
                payload={"value": "10.00"},
            )
            session.add(evento)
            await session.commit()

            total = await OutboxDispatcher(
                session=session,
                redis=redis,
                clock=SystemClock(settings.app.app_timezone),
            ).despachar_lote()

            persistido = await session.scalar(
                select(OutboxEventModel).where(OutboxEventModel.id == evento.id)
            )

        assert total == 1
        assert await redis.xlen(STREAM_DE_EVENTOS) == 1
        assert persistido is not None and persistido.processed_at is not None
    finally:
        await redis.delete(STREAM_DE_EVENTOS)
        await redis.aclose()
        await engine.dispose()
