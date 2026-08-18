"""Métricas HTTP mínimas no formato de exposição do Prometheus."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from time import perf_counter

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class HttpMetrics:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._counts: defaultdict[tuple[str, str, int], int] = defaultdict(int)
        self._durations: defaultdict[tuple[str, str], float] = defaultdict(float)

    async def registrar(self, method: str, route: str, status: int, duration: float) -> None:
        async with self._lock:
            self._counts[(method, route, status)] += 1
            self._durations[(method, route)] += duration

    async def exportar(self) -> str:
        async with self._lock:
            linhas = [
                "# HELP rfbalance_http_requests_total Total de requisições HTTP.",
                "# TYPE rfbalance_http_requests_total counter",
            ]
            for (method, route, status), quantidade in sorted(self._counts.items()):
                linhas.append(
                    f'rfbalance_http_requests_total{{method="{method}",route="{route}",'
                    f'status="{status}"}} {quantidade}'
                )
            linhas.extend(
                [
                    "# HELP rfbalance_http_request_duration_seconds_sum "
                    "Soma da duração das requisições HTTP.",
                    "# TYPE rfbalance_http_request_duration_seconds_sum counter",
                ]
            )
            for (method, route), duracao in sorted(self._durations.items()):
                linhas.append(
                    f'rfbalance_http_request_duration_seconds_sum{{method="{method}",'
                    f'route="{route}"}} {duracao:.9f}'
                )
            return "\n".join(linhas) + "\n"


METRICS = HttpMetrics()
router = APIRouter(tags=["observability"])


class HttpMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        inicio = perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            rota = request.scope.get("route")
            caminho = getattr(rota, "path", request.url.path)
            await METRICS.registrar(request.method, str(caminho), status, perf_counter() - inicio)


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> str:
    return await METRICS.exportar()
