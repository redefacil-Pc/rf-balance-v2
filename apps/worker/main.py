"""Entrypoint do worker.

A escolha da biblioteca de fila (Celery, Dramatiq ou RQ) está pendente do
ADR-0004 e não deve ser antecipada aqui. Até essa decisão, o processo apenas
publica heartbeat — o que já valida rede, configuração e observabilidade do
container sem criar acoplamento com uma fila específica.
"""

from __future__ import annotations

import asyncio

import structlog

from app.platform.config.settings import get_settings
from app.platform.observability.logging import configurar_logging

HEARTBEAT_SEGUNDOS = 30

_logger = structlog.get_logger("worker")


async def executar() -> None:
    settings = get_settings()
    settings.validar()
    configurar_logging(settings.app.log_level, settings.app.app_env)

    _logger.info("worker_iniciado", environment=settings.app.app_env, pending_adr="0004")
    while True:
        _logger.info("worker_heartbeat")
        await asyncio.sleep(HEARTBEAT_SEGUNDOS)


if __name__ == "__main__":
    asyncio.run(executar())
