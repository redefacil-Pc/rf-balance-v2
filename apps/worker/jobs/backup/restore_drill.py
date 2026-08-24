"""Restaura o backup mais recente em banco isolado e publica o resultado."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import URL, make_url

from app.platform.config.settings import Settings, get_settings
from app.platform.storage.object_storage import chave_com_prefixo, criar_cliente
from worker.jobs.backup.restore_database import _download_and_verify, _latest_key

_SAFE_DATABASE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{2,63}$")
_REQUIRED_TABLES = frozenset(
    {
        "alembic_version",
        "users",
        "roles",
        "permissions",
        "proposals",
        "receipts",
        "commission_entries",
        "audit_events",
    }
)


@dataclass(frozen=True, slots=True)
class RestoreDrillResult:
    backup_key: str
    report_key: str
    sha256: str
    restored_database: str
    table_count: int
    migration_version: str
    user_count: int
    proposal_count: int
    receipt_count: int
    checked_at: str
    status: str = "PASS"


def _client_binary() -> str:
    binary = shutil.which("mariadb") or shutil.which("mysql")
    if not binary:
        raise RuntimeError("cliente mysql/mariadb não está instalado")
    return binary


def _connection_command(url: URL, database: str | None = None) -> tuple[list[str], dict[str, str]]:
    if not url.host or not url.username:
        raise RuntimeError("destino MySQL não identifica host e usuário")
    command = [
        _client_binary(),
        "--batch",
        "--skip-column-names",
        f"--host={url.host}",
        f"--port={url.port or 3306}",
        f"--user={url.username}",
    ]
    if database:
        command.append(database)
    environment = os.environ.copy()
    if url.password:
        environment["MYSQL_PWD"] = url.password
    return command, environment


def _execute_sql(url: URL, sql: str, database: str | None = None) -> str:
    command, environment = _connection_command(url, database)
    process = subprocess.run(
        command,
        input=sql.encode("utf-8"),
        capture_output=True,
        env=environment,
        check=False,
    )
    if process.returncode:
        error = process.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"comando MySQL do ensaio falhou: {error[-1000:]}")
    return process.stdout.decode("utf-8", errors="replace").strip()


def _restore_archive(
    url: URL,
    archive: Path,
    target_database: str,
    source_database: str,
) -> None:
    command, environment = _connection_command(url, target_database)
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=environment,
    )
    if process.stdin is None:
        raise RuntimeError("cliente MySQL não abriu a entrada da restauração")
    with gzip.open(archive, "rt", encoding="utf-8", errors="replace") as source:
        for line in source:
            stripped = line.strip()
            if stripped.startswith("CREATE DATABASE"):
                continue
            if stripped == f"USE `{source_database}`;":
                continue
            process.stdin.write(line.encode("utf-8"))
    process.stdin.close()
    stderr = process.stderr.read() if process.stderr else b""
    return_code = process.wait()
    if return_code:
        error = stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"restauração do ensaio falhou: {error[-1000:]}")


def run_restore_drill(settings: Settings, key: str | None = None) -> RestoreDrillResult:
    storage = settings.storage
    database = storage.backup_restore_database
    source_database = make_url(settings.database.migration_url).database
    if (
        not _SAFE_DATABASE.fullmatch(database)
        or not source_database
        or database == source_database
    ):
        raise RuntimeError("BACKUP_RESTORE_DATABASE é inseguro ou aponta para o banco principal")
    if not storage.backup_bucket:
        raise RuntimeError("BACKUP_BUCKET não foi configurado")

    client = criar_cliente(storage)
    backup_key = key or _latest_key(client, storage.backup_bucket, storage.backup_prefix)
    expected_prefix = chave_com_prefixo("database/", storage.backup_prefix)
    if not backup_key.startswith(expected_prefix) or not backup_key.endswith(".sql.gz"):
        raise RuntimeError("a chave está fora do namespace de backups do banco")

    url = make_url(settings.database.migration_url)
    checked_at = datetime.now(UTC)
    with tempfile.TemporaryDirectory(prefix="rfbalance-restore-drill-") as directory:
        archive = Path(directory) / "database.sql.gz"
        digest = _download_and_verify(client, storage.backup_bucket, backup_key, archive)
        _execute_sql(
            url,
            f"DROP DATABASE IF EXISTS `{database}`; "
            f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;",
        )
        try:
            _restore_archive(url, archive, database, source_database)
            tables = set(_execute_sql(url, "SHOW TABLES;", database).splitlines())
            missing = sorted(_REQUIRED_TABLES - tables)
            if missing:
                raise RuntimeError(f"restauração sem tabelas obrigatórias: {', '.join(missing)}")
            migration = _execute_sql(url, "SELECT version_num FROM alembic_version;", database)
            if not migration:
                raise RuntimeError("restauração sem versão de migration")
            counts = _execute_sql(
                url,
                "SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM proposals; "
                "SELECT COUNT(*) FROM receipts;",
                database,
            ).splitlines()
            if len(counts) != 3:
                raise RuntimeError("consultas de conferência retornaram resultado incompleto")
        finally:
            _execute_sql(url, f"DROP DATABASE IF EXISTS `{database}`;")

    report_key = chave_com_prefixo(
        f"restore-tests/{checked_at:%Y/%m/%d}/restore-{checked_at:%Y%m%dT%H%M%SZ}.json",
        storage.backup_prefix,
    )
    result = RestoreDrillResult(
        backup_key=backup_key,
        report_key=report_key,
        sha256=digest,
        restored_database=database,
        table_count=len(tables),
        migration_version=migration,
        user_count=int(counts[0]),
        proposal_count=int(counts[1]),
        receipt_count=int(counts[2]),
        checked_at=checked_at.isoformat(),
    )
    client.put_object(
        Bucket=storage.backup_bucket,
        Key=report_key,
        Body=json.dumps(asdict(result), ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    return result


def restore_drill_exists_on(settings: Settings, day: datetime) -> bool:
    prefix = chave_com_prefixo(
        f"restore-tests/{day.astimezone(UTC):%Y/%m/%d}/",
        settings.storage.backup_prefix,
    )
    response = criar_cliente(settings.storage).list_objects_v2(
        Bucket=settings.storage.backup_bucket,
        Prefix=prefix,
        MaxKeys=1,
    )
    return bool(response.get("KeyCount", 0))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", help="backup específico; por padrão usa o mais recente")
    args = parser.parse_args()
    print(json.dumps(asdict(run_restore_drill(get_settings(), args.key)), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
