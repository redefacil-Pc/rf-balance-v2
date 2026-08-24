"""Backup lógico diário do MySQL em object storage compatível com S3."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url

from app.platform.config.settings import Settings, get_settings
from app.platform.storage.object_storage import chave_com_prefixo, criar_cliente


@dataclass(frozen=True, slots=True)
class BackupResult:
    bucket: str
    key: str
    manifest_key: str
    sha256: str
    compressed_bytes: int
    created_at: str
    removed_by_retention: int
    local_replica_path: str | None = None


def _dump_binary() -> str:
    binary = shutil.which("mariadb-dump") or shutil.which("mysqldump")
    if not binary:
        raise RuntimeError("mariadb-dump/mysqldump não está instalado no worker")
    return binary


def _create_compressed_dump(database_url: str, destination: Path) -> None:
    url = make_url(database_url)
    if not url.host or not url.database or not url.username:
        raise RuntimeError("MIGRATION_DATABASE_URL não identifica host, banco e usuário")

    command = [
        _dump_binary(),
        "--single-transaction",
        "--quick",
        "--routines",
        "--triggers",
        "--no-tablespaces",
        "--hex-blob",
        "--default-character-set=utf8mb4",
        "--skip-lock-tables",
        f"--host={url.host}",
        f"--port={url.port or 3306}",
        f"--user={url.username}",
        url.database,
    ]
    environment = os.environ.copy()
    if url.password:
        environment["MYSQL_PWD"] = url.password

    with tempfile.NamedTemporaryFile(suffix=".sql", delete=False) as raw_file:
        raw_path = Path(raw_file.name)
        process = subprocess.run(
            command,
            stdout=raw_file,
            stderr=subprocess.PIPE,
            env=environment,
            check=False,
        )
    try:
        if process.returncode:
            error = process.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"dump do MySQL falhou: {error[-1000:]}")
        with raw_path.open("rb") as source, gzip.open(destination, "wb", compresslevel=6) as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)
    finally:
        raw_path.unlink(missing_ok=True)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _store_local_replica(
    archive: Path,
    *,
    key: str,
    backup_prefix: str,
    replica_dir: str,
    sha256: str,
    retention_days: int,
    now: datetime,
) -> str | None:
    if not replica_dir.strip():
        return None
    root = Path(replica_dir).resolve()
    prefix = f"{backup_prefix.strip().strip('/')}/"
    if not key.startswith(prefix):
        raise RuntimeError("chave do backup fora do namespace da réplica local")
    relative = Path(key.removeprefix(prefix))
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("caminho inseguro para a réplica local")
    destination = (root / relative).resolve()
    if root not in destination.parents:
        raise RuntimeError("destino da réplica escapou do diretório autorizado")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{destination.suffix}.tmp")
    shutil.copyfile(archive, temporary)
    if _sha256_file(temporary) != sha256:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("SHA-256 da réplica local não confere")
    temporary.replace(destination)
    destination.with_suffix(f"{destination.suffix}.sha256").write_text(
        f"{sha256}  {destination.name}\n", encoding="ascii"
    )

    cutoff = (now - timedelta(days=retention_days)).timestamp()
    for candidate in root.rglob("*"):
        if candidate.is_file() and candidate.stat().st_mtime < cutoff:
            candidate.unlink()
    return str(destination.relative_to(root))


def _verify_remote(client: Any, bucket: str, key: str, expected_sha256: str) -> None:
    response = client.get_object(Bucket=bucket, Key=key)
    digest = hashlib.sha256()
    body = response["Body"]
    try:
        for chunk in iter(lambda: body.read(1024 * 1024), b""):
            digest.update(chunk)
    finally:
        body.close()
    if digest.hexdigest() != expected_sha256:
        raise RuntimeError("o SHA-256 do backup enviado não confere")


def _remove_expired(
    client: Any,
    *,
    bucket: str,
    prefix: str,
    retention_days: int,
    now: datetime,
) -> int:
    cutoff = now - timedelta(days=retention_days)
    removed = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=f"{prefix.rstrip('/')}/"):
        expired = [
            {"Key": item["Key"]}
            for item in page.get("Contents", [])
            if item["LastModified"].astimezone(UTC) < cutoff
        ]
        if expired:
            client.delete_objects(Bucket=bucket, Delete={"Objects": expired, "Quiet": True})
            removed += len(expired)
    return removed


def backup_exists_today(settings: Settings, now: datetime | None = None) -> bool:
    if not settings.storage.backup_bucket:
        return False
    current = (now or datetime.now(UTC)).astimezone(UTC)
    date_prefix = chave_com_prefixo(
        f"database/{current:%Y/%m/%d}/",
        settings.storage.backup_prefix,
    )
    client = criar_cliente(settings.storage)
    response = client.list_objects_v2(
        Bucket=settings.storage.backup_bucket,
        Prefix=date_prefix,
        MaxKeys=10,
    )
    return any(item["Key"].endswith(".sql.gz") for item in response.get("Contents", []))


def create_database_backup(settings: Settings, now: datetime | None = None) -> BackupResult:
    if not settings.storage.backup_bucket:
        raise RuntimeError("BACKUP_BUCKET não foi configurado")

    current = (now or datetime.now(UTC)).astimezone(UTC)
    timestamp = current.strftime("%Y%m%dT%H%M%SZ")
    key = chave_com_prefixo(
        f"database/{current:%Y/%m/%d}/rfbalance-{timestamp}.sql.gz",
        settings.storage.backup_prefix,
    )
    manifest_key = f"{key}.json"
    client = criar_cliente(settings.storage)

    with tempfile.TemporaryDirectory(prefix="rfbalance-backup-") as directory:
        archive = Path(directory) / "database.sql.gz"
        _create_compressed_dump(settings.database.migration_url, archive)
        sha256 = _sha256_file(archive)
        size = archive.stat().st_size
        with archive.open("rb") as body:
            client.put_object(
                Bucket=settings.storage.backup_bucket,
                Key=key,
                Body=body,
                ContentType="application/gzip",
                Metadata={"sha256": sha256, "created-at": current.isoformat()},
            )
        _verify_remote(client, settings.storage.backup_bucket, key, sha256)
        local_replica_path = _store_local_replica(
            archive,
            key=key,
            backup_prefix=settings.storage.backup_prefix,
            replica_dir=settings.storage.backup_local_replica_dir,
            sha256=sha256,
            retention_days=settings.storage.backup_retention_days,
            now=current,
        )

    manifest = {
        "version": 1,
        "format": "mysql-logical-sql-gzip",
        "database": make_url(settings.database.migration_url).database,
        "object_key": key,
        "sha256": sha256,
        "compressed_bytes": size,
        "created_at": current.isoformat(),
        "verified_after_upload": True,
    }
    client.put_object(
        Bucket=settings.storage.backup_bucket,
        Key=manifest_key,
        Body=json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    removed = _remove_expired(
        client,
        bucket=settings.storage.backup_bucket,
        prefix=settings.storage.backup_prefix,
        retention_days=settings.storage.backup_retention_days,
        now=current,
    )
    return BackupResult(
        bucket=settings.storage.backup_bucket,
        key=key,
        manifest_key=manifest_key,
        sha256=sha256,
        compressed_bytes=size,
        created_at=current.isoformat(),
        removed_by_retention=removed,
        local_replica_path=local_replica_path,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="cria mesmo se já houver backup hoje")
    args = parser.parse_args()
    settings = get_settings()
    now = datetime.now(UTC)
    if not args.force and backup_exists_today(settings, now):
        print("backup de hoje já existe")
        return 0
    result = create_database_backup(settings, now)
    print(json.dumps(asdict(result), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
