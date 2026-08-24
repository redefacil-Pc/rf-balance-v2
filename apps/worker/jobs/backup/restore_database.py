"""Verifica um backup e, com confirmação explícita, restaura o MySQL."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import IO, Any, cast

from sqlalchemy.engine import make_url

from app.platform.config.settings import get_settings
from app.platform.storage.object_storage import chave_com_prefixo, criar_cliente


def _latest_key(client: Any, bucket: str, prefix: str) -> str:
    paginator = client.get_paginator("list_objects_v2")
    keys: list[tuple[Any, str]] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=f"{prefix.rstrip('/')}/database/"):
        keys.extend(
            (item["LastModified"], item["Key"])
            for item in page.get("Contents", [])
            if item["Key"].endswith(".sql.gz")
        )
    if not keys:
        raise RuntimeError("nenhum backup de banco foi encontrado")
    return max(keys)[1]


def _download_and_verify(client: Any, bucket: str, key: str, target: Path) -> str:
    response = client.get_object(Bucket=bucket, Key=key)
    expected = response.get("Metadata", {}).get("sha256")
    digest = hashlib.sha256()
    with target.open("wb") as file:
        body = response["Body"]
        try:
            for chunk in iter(lambda: body.read(1024 * 1024), b""):
                digest.update(chunk)
                file.write(chunk)
        finally:
            body.close()
    actual = digest.hexdigest()
    if not expected or actual != expected:
        raise RuntimeError("SHA-256 ausente ou divergente; restauração recusada")
    with gzip.open(target, "rb") as archive:
        for _ in iter(lambda: archive.read(1024 * 1024), b""):
            pass
    return actual


def _restore(archive: Path, database_url: str) -> None:
    url = make_url(database_url)
    binary = shutil.which("mariadb") or shutil.which("mysql")
    if not binary or not url.host or not url.username:
        raise RuntimeError("cliente MySQL ou destino de restauração indisponível")
    command = [
        binary,
        f"--host={url.host}",
        f"--port={url.port or 3306}",
        f"--user={url.username}",
    ]
    environment = os.environ.copy()
    if url.password:
        environment["MYSQL_PWD"] = url.password
    with gzip.open(archive, "rb") as source:
        process = subprocess.run(
            command,
            stdin=cast(IO[bytes], source),
            stderr=subprocess.PIPE,
            env=environment,
            check=False,
        )
    if process.returncode:
        error = process.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"restauração falhou: {error[-1000:]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", help="chave do .sql.gz; por padrão usa o mais recente")
    parser.add_argument("--restore", action="store_true", help="restaura após verificar")
    parser.add_argument("--confirm", help="para restaurar, informe exatamente RESTAURAR")
    args = parser.parse_args()
    settings = get_settings()
    bucket = settings.storage.backup_bucket
    if not bucket:
        raise RuntimeError("BACKUP_BUCKET não foi configurado")
    client = criar_cliente(settings.storage)
    key = args.key or _latest_key(client, bucket, settings.storage.backup_prefix)
    expected_prefix = chave_com_prefixo("database/", settings.storage.backup_prefix)
    if not key.startswith(expected_prefix) or not key.endswith(".sql.gz"):
        raise RuntimeError("a chave informada está fora do namespace de backups do banco")

    with tempfile.TemporaryDirectory(prefix="rfbalance-restore-") as directory:
        archive = Path(directory) / "database.sql.gz"
        digest = _download_and_verify(client, bucket, key, archive)
        print(f"backup íntegro: {key} sha256={digest}")
        if args.restore:
            if args.confirm != "RESTAURAR":
                raise RuntimeError("restauração recusada: use --confirm RESTAURAR")
            _restore(archive, settings.database.migration_url)
            print("restauração concluída")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
