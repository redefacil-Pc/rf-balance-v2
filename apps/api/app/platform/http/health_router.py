"""Rotas de health.

`/health/live` não toca dependência alguma — responde se o processo está vivo.
`/health/ready` verifica banco, migração esperada, Redis e storage.
São as duas únicas rotas públicas da API; todo o resto é deny by default.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.platform.observability.readiness import montar_relatorio

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    estado = request.app.state
    relatorio = await montar_relatorio(
        engine=estado.engine,
        redis=estado.redis,
        storage=estado.storage,
        bucket=estado.settings.storage.object_storage_bucket,
        # cada módulo pluga a sua verificação no `main`; a plataforma não sabe
        # quais são nem precisa saber
        extras=getattr(estado, "readiness_extras", ()),
    )
    return JSONResponse(
        status_code=200 if relatorio.ok else 503,
        content=relatorio.para_dicionario(),
    )
