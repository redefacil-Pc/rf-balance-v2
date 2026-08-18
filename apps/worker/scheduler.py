"""Scheduler de réplica única, protegido por lease no Redis."""

from __future__ import annotations

import asyncio
import uuid

import structlog

from app.platform.cache.redis_client import criar_cliente
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes
from app.platform.observability.logging import configurar_logging
from worker.jobs.integrity.check_f2_integrity import executar as verificar_integridade

TICK_SEGUNDOS = 60
LOCK_SEGUNDOS = 90
CHAVE_DE_LIDER = "rfbalance:scheduler:leader"

_logger = structlog.get_logger("scheduler")


async def executar() -> None:
    settings = get_settings()
    settings.validar()
    configurar_logging(settings.app.log_level, settings.app.app_env)

    redis = criar_cliente(settings.redis)
    engine = criar_engine(settings.database)
    sessoes = criar_fabrica_de_sessoes(engine)
    token = uuid.uuid4().hex
    _logger.info("scheduler_iniciado", environment=settings.app.app_env)
    try:
        while True:
            adquiriu = await redis.set(CHAVE_DE_LIDER, token, ex=LOCK_SEGUNDOS, nx=True)
            if adquiriu:
                async with sessoes() as session:
                    resultados = await verificar_integridade(session)
                _logger.info("scheduler_tick", scheduled_jobs=1, leader=True, **resultados)
            elif await redis.get(CHAVE_DE_LIDER) == token:
                await redis.expire(CHAVE_DE_LIDER, LOCK_SEGUNDOS)
                async with sessoes() as session:
                    resultados = await verificar_integridade(session)
                _logger.info("scheduler_tick", scheduled_jobs=1, leader=True, **resultados)
            else:
                _logger.info("scheduler_standby", leader=False)
            await asyncio.sleep(TICK_SEGUNDOS)
    finally:
        if await redis.get(CHAVE_DE_LIDER) == token:
            await redis.delete(CHAVE_DE_LIDER)
        await redis.aclose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(executar())
