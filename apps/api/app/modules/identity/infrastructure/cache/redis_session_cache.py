"""Cache da resolução sessão -> usuário no Redis (ADR-0003).

Guarda apenas identidade e permissões — nunca hash de senha, valor financeiro ou
PII além do nome. TTL curto: revogação leva no máximo `session_cache_ttl`
segundos para refletir, e `invalidar` derruba na hora.
"""

from __future__ import annotations

import json

from redis.asyncio import Redis

from app.modules.identity.domain.entities.user import User
from app.modules.identity.domain.value_objects.email_address import EmailAddress

PREFIXO = "session:"


class RedisSessionCache:
    __slots__ = ("_redis",)

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def obter(self, token_hash: str) -> User | None:
        bruto = await self._redis.get(PREFIXO + token_hash)
        if not bruto:
            return None
        dados = json.loads(bruto)
        return User(
            id=dados["id"],
            email=EmailAddress(dados["email"]),
            full_name=dados["full_name"],
            password_hash="",  # nunca cacheado
            is_active=dados["is_active"],
            must_change_password=dados["must_change_password"],
            roles=frozenset(dados["roles"]),
            permissions=frozenset(dados["permissions"]),
        )

    async def guardar(self, token_hash: str, user: User, ttl_segundos: int) -> None:
        if ttl_segundos <= 0:
            return
        payload = json.dumps(
            {
                "id": user.id,
                "email": user.email.valor,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "must_change_password": user.must_change_password,
                "roles": sorted(user.roles),
                "permissions": sorted(user.permissions),
            }
        )
        await self._redis.set(PREFIXO + token_hash, payload, ex=ttl_segundos)

    async def invalidar(self, token_hash: str) -> None:
        await self._redis.delete(PREFIXO + token_hash)
