from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from app.platform.config.security import CSRF_COOKIE, CSRF_HEADER
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes
from app.platform.time.clock import SystemClock
from worker.jobs.documents.financial_report_batch import FinancialReportBatchProcessor

pytestmark = pytest.mark.integration


class _Body:
    def __init__(self, content: bytes) -> None:
        self._content = content

    def iter_chunks(self, chunk_size: int) -> Any:
        for start in range(0, len(self._content), chunk_size):
            yield self._content[start : start + chunk_size]


class _Storage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_object(self, **kwargs: Any) -> None:
        self.objects[str(kwargs["Key"])] = bytes(kwargs["Body"])

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        return {"Body": _Body(self.objects[str(kwargs["Key"])])}


async def test_lote_idempotente_e_download_do_zip(
    cliente: AsyncClient,
    app_em_teste: Any,
    admin_semeado: dict[str, str],
) -> None:
    login = await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )
    assert login.status_code == 200
    headers = {CSRF_HEADER: cliente.cookies[CSRF_COOKIE], "Idempotency-Key": "batch-test-001"}
    body = {"period_start": "2026-08-01", "period_end": "2026-08-07"}

    created = await cliente.post("/api/v1/document-jobs", json=body, headers=headers)
    assert created.status_code == 202, created.text
    job_id = created.json()["id"]
    repeated = await cliente.post("/api/v1/document-jobs", json=body, headers=headers)
    assert repeated.status_code == 202
    assert repeated.json()["id"] == job_id
    conflict = await cliente.post(
        "/api/v1/document-jobs",
        json={"period_start": "2026-08-08", "period_end": "2026-08-14"},
        headers=headers,
    )
    assert conflict.status_code == 409

    settings = get_settings()
    storage = _Storage()
    app_em_teste.state.storage = storage
    engine = criar_engine(settings.database)
    sessions = criar_fabrica_de_sessoes(engine)
    try:
        async with sessions() as session:
            processed = await FinancialReportBatchProcessor(
                session=session,
                storage=storage,
                storage_settings=settings.storage,
                clock=SystemClock(settings.app.app_timezone),
            ).process_next()
            assert processed is True
    finally:
        await engine.dispose()

    detail = await cliente.get(f"/api/v1/document-jobs/{job_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "COMPLETED"
    assert detail.json()["archive_ready"] is True
    assert detail.json()["processed_items"] == 0

    downloaded = await cliente.get(f"/api/v1/document-jobs/{job_id}/download")
    assert downloaded.status_code == 200, downloaded.text
    assert downloaded.headers["content-type"] == "application/zip"
    assert downloaded.content.startswith(b"PK")
