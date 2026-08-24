from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.modules.operations.api import routes
from app.modules.operations.api.schemas import BackupSummary
from app.platform.config.security import CSRF_COOKIE, CSRF_HEADER
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from worker.jobs.backup.database_backup import BackupResult

pytestmark = pytest.mark.integration


async def test_admin_consulta_operacoes_e_executa_backup_auditado(
    cliente: AsyncClient,
    admin_semeado: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 8, 21, 13, 47, tzinfo=UTC)
    monkeypatch.setattr(
        routes,
        "_last_backup",
        lambda *_: BackupSummary(
            key="backups/database/2026/08/21/database.sql.gz",
            created_at=now,
            compressed_bytes=8192,
            sha256="a" * 64,
            verified=True,
        ),
    )
    monkeypatch.setattr(routes, "_versioning_enabled", lambda *_: True)
    monkeypatch.setattr(
        routes,
        "create_database_backup",
        lambda *_: BackupResult(
            bucket="bucket-test",
            key="backups/database/2026/08/21/manual.sql.gz",
            manifest_key="backups/database/2026/08/21/manual.sql.gz.json",
            sha256="b" * 64,
            compressed_bytes=9216,
            created_at=now.isoformat(),
            removed_by_retention=2,
            local_replica_path="database/2026/08/21/manual.sql.gz",
        ),
    )
    engine = criar_engine(get_settings().database)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO data_integrity_checks "
                "(check_type,status,details,checked_at) VALUES "
                "('team_assignment_overlaps','PASS',JSON_OBJECT('count',0),:checked_at)"
            ),
            {"checked_at": now},
        )
    await engine.dispose()

    login = await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )
    assert login.status_code == 200

    status = await cliente.get("/api/v1/admin/operations")
    assert status.status_code == 200, status.text
    assert status.json()["backup"]["last_backup"]["verified"] is True
    assert status.json()["integrity_checks"][0]["status"] == "PASS"

    created = await cliente.post(
        "/api/v1/admin/operations/backups",
        headers={CSRF_HEADER: cliente.cookies[CSRF_COOKIE]},
    )
    assert created.status_code == 201, created.text
    assert created.json()["compressed_bytes"] == 9216
    assert created.json()["removed_by_retention"] == 2
    assert created.json()["local_replica_created"] is True

    audit = await cliente.get("/api/v1/audit-events", params={"action": "backup.created_manually"})
    assert audit.status_code == 200
    assert audit.json()["items"][0]["aggregate_id"].endswith("manual.sql.gz")


async def test_operacoes_exigem_sessao(cliente: AsyncClient) -> None:
    response = await cliente.get("/api/v1/admin/operations")
    assert response.status_code == 401
