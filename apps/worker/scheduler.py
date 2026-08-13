"""Entrypoint do scheduler.

Agenda única do sistema. A API roda sem scheduler embutido (seção 12.2), e este
processo precisa de leader election antes de rodar com mais de uma réplica —
enquanto isso não existir, manter `scheduler` em réplica única.

Tarefas previstas: reconciliação de read models, verificação de integridade,
backup, limpeza de documentos expirados. Implementação depende do ADR-0004.
"""

from __future__ import annotations

import asyncio

import structlog

from app.platform.config.settings import get_settings
from app.platform.observability.logging import configurar_logging

TICK_SEGUNDOS = 60

_logger = structlog.get_logger("scheduler")


async def executar() -> None:
    settings = get_settings()
    settings.validar()
    configurar_logging(settings.app.log_level, settings.app.app_env)

    _logger.info("scheduler_iniciado", environment=settings.app.app_env, pending_adr="0004")
    while True:
        _logger.info("scheduler_tick", scheduled_jobs=0)
        await asyncio.sleep(TICK_SEGUNDOS)


if __name__ == "__main__":
    asyncio.run(executar())
