from __future__ import annotations

import math
import os
from time import perf_counter

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.performance

SAMPLES = 20
DASHBOARD_PARAMS = {"period_start": "2023-01-01", "period_end": "2025-12-31"}
REPORT_PARAMS = {"period_start": "2025-10-01", "period_end": "2025-12-31"}


def _p95(samples: list[float]) -> float:
    return sorted(samples)[math.ceil(len(samples) * 0.95) - 1]


async def _measure(client: AsyncClient, path: str, params: dict[str, str]) -> tuple[float, int]:
    warmup = await client.get(path, params=params)
    assert warmup.status_code == 200, warmup.text
    samples: list[float] = []
    response_size = 0
    for _ in range(SAMPLES):
        start = perf_counter()
        response = await client.get(path, params=params)
        samples.append(perf_counter() - start)
        assert response.status_code == 200, response.text
        response_size = len(response.content)
    return _p95(samples), response_size


async def test_dashboard_p95(performance_client: AsyncClient) -> None:
    p95, response_size = await _measure(performance_client, "/api/v1/dashboard", DASHBOARD_PARAMS)
    budget = float(os.getenv("PERFORMANCE_DASHBOARD_P95_SECONDS", "2.0"))
    print(f"dashboard_p95={p95:.4f}s budget={budget:.4f}s bytes={response_size}")
    assert p95 <= budget


async def test_financial_report_p95(performance_client: AsyncClient) -> None:
    p95, response_size = await _measure(
        performance_client, "/api/v1/commission-financial-report", REPORT_PARAMS
    )
    budget = float(os.getenv("PERFORMANCE_REPORT_P95_SECONDS", "5.0"))
    print(f"report_p95={p95:.4f}s budget={budget:.4f}s bytes={response_size}")
    assert p95 <= budget
