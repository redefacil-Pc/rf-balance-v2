"""Contribuição do `identity` ao readiness: o RBAC do banco reflete o catálogo?

Mesma lógica de `verificar_migracao`: código e banco fora de sincronia é erro
silencioso. Aqui o sintoma seria pior que uma exceção — seria um 403 correto na
forma e errado no mérito, que se investiga como bug de permissão do usuário e
não como banco defasado.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.identity.infrastructure import rbac_sync
from app.platform.observability.readiness import CheckResult

NOME_DO_CHECK = "rbac"

FabricaDeSessoes = async_sessionmaker[AsyncSession]


async def verificar_rbac(fabrica: FabricaDeSessoes) -> CheckResult:
    try:
        async with fabrica() as session:
            divergencia = await rbac_sync.verificar(session)
    except Exception as exc:
        return CheckResult(NOME_DO_CHECK, False, type(exc).__name__)

    return CheckResult(NOME_DO_CHECK, divergencia.sincronizado, divergencia.resumo())


def montar_check(fabrica: FabricaDeSessoes) -> Callable[[], Awaitable[CheckResult]]:
    """Fecha a fábrica de sessões no formato que o readiness espera."""

    async def check() -> CheckResult:
        return await verificar_rbac(fabrica)

    return check
