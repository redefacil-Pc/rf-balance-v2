"""Worker que entrega a outbox transacional ao Redis Streams."""

from __future__ import annotations

import asyncio

import structlog

import app.platform.db.models_registry  # noqa: F401 — registra FKs usadas pelo worker
from app.platform.bus.outbox_dispatcher import OutboxDispatcher
from app.platform.cache.redis_client import criar_cliente
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes
from app.platform.observability.logging import configurar_logging
from app.platform.storage.object_storage import criar_cliente as criar_storage
from app.platform.time.clock import SystemClock
from worker.jobs.documents.financial_report_batch import FinancialReportBatchProcessor

INTERVALO_OCIOSO_SEGUNDOS = 2

_logger = structlog.get_logger("worker")


async def executar() -> None:
    settings = get_settings()
    settings.validar()
    configurar_logging(settings.app.log_level, settings.app.app_env)

    engine = criar_engine(settings.database)
    sessoes = criar_fabrica_de_sessoes(engine)
    redis = criar_cliente(settings.redis)
    storage = criar_storage(settings.storage)
    clock = SystemClock(settings.app.app_timezone)
    _logger.info("worker_iniciado", environment=settings.app.app_env, transport="redis-streams")
    try:
        while True:
            async with sessoes() as session:
                quantidade = await OutboxDispatcher(
                    session=session,
                    redis=redis,
                    clock=clock,
                    maxlen=settings.retention.redis_stream_maxlen,
                ).despachar_lote()
            async with sessoes() as session:
                document_processed = await FinancialReportBatchProcessor(
                    session=session,
                    storage=storage,
                    storage_settings=settings.storage,
                    clock=clock,
                ).process_next()
            if quantidade:
                _logger.info("outbox_despachada", quantidade=quantidade)
            if not quantidade and not document_processed:
                await asyncio.sleep(INTERVALO_OCIOSO_SEGUNDOS)
    finally:
        await redis.aclose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(executar())
