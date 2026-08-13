"""Verificação de dependências essenciais para o readiness (seção 12.5)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.platform.db.migration_state import esta_sincronizado
from app.platform.storage.object_storage import bucket_acessivel


@dataclass(frozen=True, slots=True)
class CheckResult:
    nome: str
    ok: bool
    detalhe: str = ""


#: Verificação que um módulo contribui ao readiness. A plataforma não conhece
#: `identity`, `commercial` e afins — quem compõe é o `main`, e o contrato entre
#: os dois é só esta assinatura.
CheckExtra = Callable[[], Awaitable[CheckResult]]


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    checks: list[CheckResult]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def para_dicionario(self) -> dict[str, object]:
        return {
            "status": "ready" if self.ok else "not_ready",
            "checks": [{"name": c.nome, "ok": c.ok, "detail": c.detalhe} for c in self.checks],
        }


async def verificar_banco(engine: AsyncEngine) -> CheckResult:
    try:
        async with engine.connect() as conexao:
            await conexao.execute(text("SELECT 1"))
    except Exception as exc:
        return CheckResult("database", False, type(exc).__name__)
    return CheckResult("database", True)


async def verificar_migracao(engine: AsyncEngine) -> CheckResult:
    try:
        sincronizado, esperada, aplicada = await esta_sincronizado(engine)
    except Exception as exc:
        return CheckResult("migration", False, type(exc).__name__)
    return CheckResult(
        "migration",
        sincronizado,
        "" if sincronizado else f"esperada={esperada} aplicada={aplicada}",
    )


async def verificar_redis(cliente: Redis) -> CheckResult:
    try:
        await cliente.ping()
    except Exception as exc:
        return CheckResult("redis", False, type(exc).__name__)
    return CheckResult("redis", True)


async def verificar_storage(cliente: object, bucket: str) -> CheckResult:
    ok = await asyncio.to_thread(bucket_acessivel, cliente, bucket)
    return CheckResult("storage", ok, "" if ok else f"bucket={bucket}")


async def montar_relatorio(
    *,
    engine: AsyncEngine,
    redis: Redis,
    storage: object,
    bucket: str,
    extras: Sequence[CheckExtra] = (),
) -> ReadinessReport:
    checks = await asyncio.gather(
        verificar_banco(engine),
        verificar_migracao(engine),
        verificar_redis(redis),
        verificar_storage(storage, bucket),
        *(extra() for extra in extras),
    )
    return ReadinessReport(checks=list(checks))
