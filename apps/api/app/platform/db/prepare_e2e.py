"""Prepara exclusivamente o banco rfbalance_test para o teste de navegador."""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.modules.identity.infrastructure import seed_identity
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes
from tests.integration.conftest import TABELAS_LIMPAS


async def execute() -> None:
    settings = get_settings()
    database_name = make_url(settings.database.database_url).database
    if database_name != "rfbalance_test":
        raise RuntimeError("prepare_e2e só pode operar no banco rfbalance_test")
    engine = criar_engine(settings.database)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            for table in TABELAS_LIMPAS:
                await connection.execute(text(f"TRUNCATE TABLE {table}"))
            await connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        factory = criar_fabrica_de_sessoes(engine)
        async with factory() as session:
            os.environ.setdefault("SEED_ADMIN_PASSWORD", "e2e-admin-password-2026")
            await seed_identity.semear(session)
            await session.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(execute())
