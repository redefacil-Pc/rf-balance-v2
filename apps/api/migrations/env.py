"""Ambiente do Alembic.

Usa a conta de migração (MIGRATION_DATABASE_URL), distinta da conta da
aplicação. `create_all` é proibido: o schema só muda por revisão versionada.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

from app.platform.config.database import DatabaseSettings
from app.platform.db import models_registry  # noqa: F401  (popula o metadata)
from app.platform.db.metadata import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", DatabaseSettings().migration_url)

target_metadata = Base.metadata


def _configurar(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
        include_schemas=False,
        # tipos próprios são renderizados pelo nome da classe; o import fixo está
        # em script.py.mako
        user_module_prefix="",
    )


def executar_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def executar_online() -> None:
    engine = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )
    async with engine.connect() as conexao:
        await conexao.run_sync(lambda sync_conn: _configurar(sync_conn))
        await conexao.run_sync(lambda _: context.run_migrations())
    await engine.dispose()


if context.is_offline_mode():
    executar_offline()
else:
    asyncio.run(executar_online())
