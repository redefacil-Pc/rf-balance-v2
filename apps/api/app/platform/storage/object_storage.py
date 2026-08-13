"""Object storage compatível com S3 (MinIO em local, S3 em produção)."""

from __future__ import annotations

from typing import Any

import boto3
from botocore.client import Config as BotoConfig

from app.platform.config.storage import StorageSettings


def criar_cliente(settings: StorageSettings) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.object_storage_endpoint or None,
        aws_access_key_id=settings.object_storage_access_key or None,
        aws_secret_access_key=settings.object_storage_secret_key or None,
        region_name=settings.object_storage_region,
        config=BotoConfig(
            signature_version="s3v4",
            s3={"addressing_style": settings.object_storage_addressing_style},
            connect_timeout=2,
            read_timeout=5,
            retries={"max_attempts": 2},
        ),
    )


def bucket_acessivel(cliente: Any, bucket: str) -> bool:
    try:
        cliente.head_bucket(Bucket=bucket)
    except Exception:
        return False
    return True
