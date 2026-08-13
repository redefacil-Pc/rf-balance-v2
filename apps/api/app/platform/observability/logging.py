"""Log estruturado em JSON (seção 14.1 do blueprint).

Nunca logar token, PII crua ou payload financeiro completo.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configurar_logging(log_level: str, app_env: str) -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _adicionar_ambiente(app_env),
    ]
    processors.append(
        structlog.dev.ConsoleRenderer()
        if app_env == "local"
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _adicionar_ambiente(app_env: str) -> structlog.typing.Processor:
    def processor(
        _logger: object, _name: str, event_dict: structlog.typing.EventDict
    ) -> structlog.typing.EventDict:
        event_dict["environment"] = app_env
        return event_dict

    return processor
