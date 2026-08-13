"""Cliente Redis — fila, cache e locks curtos.

Cache guarda apenas dado reconstruível. Valor financeiro autoritativo nunca é
servido do cache.
"""

from __future__ import annotations

from typing import cast

from redis.asyncio import Redis

from app.platform.config.redis import RedisSettings


def criar_cliente(settings: RedisSettings) -> Redis:
    # `Redis.from_url` não é tipada na redis-py; o cast mantém o resto do
    # código sob mypy strict sem afrouxar a configuração global
    cliente = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=30,
    )
    return cast(Redis, cliente)
