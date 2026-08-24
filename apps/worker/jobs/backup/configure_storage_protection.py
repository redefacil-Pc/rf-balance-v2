"""Configura versionamento e lifecycle do namespace de backups no Spaces."""

from __future__ import annotations

import argparse
import json

from botocore.exceptions import ClientError

from app.platform.config.settings import get_settings
from app.platform.storage.object_storage import criar_cliente, normalizar_prefixo

RULE_ID = "rfbalance-backup-retention"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="aplica; sem a flag apenas exibe")
    args = parser.parse_args()
    settings = get_settings()
    storage = settings.storage
    if not storage.backup_bucket:
        raise RuntimeError("BACKUP_BUCKET não foi configurado")
    client = criar_cliente(storage)
    try:
        current = client.get_bucket_lifecycle_configuration(Bucket=storage.backup_bucket)
        rules = [rule for rule in current.get("Rules", []) if rule.get("ID") != RULE_ID]
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code not in {"NoSuchLifecycleConfiguration", "NoSuchLifecycle"}:
            raise
        rules = []

    prefix = f"{normalizar_prefixo(storage.backup_prefix)}/"
    desired = {
        "ID": RULE_ID,
        "Status": "Enabled",
        "Filter": {"Prefix": prefix},
        "Expiration": {"Days": storage.backup_retention_days},
        "NoncurrentVersionExpiration": {"NoncurrentDays": 7},
        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
    }
    if args.apply:
        client.put_bucket_versioning(
            Bucket=storage.backup_bucket,
            VersioningConfiguration={"Status": "Enabled"},
        )
        client.put_bucket_lifecycle_configuration(
            Bucket=storage.backup_bucket,
            LifecycleConfiguration={"Rules": [*rules, desired]},
        )
    print(
        json.dumps(
            {
                "applied": args.apply,
                "bucket": storage.backup_bucket,
                "versioning": "Enabled",
                "rule": desired,
                "preserved_rule_count": len(rules),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
