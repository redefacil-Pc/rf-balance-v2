"""Fábrica de sessões assíncronas.

A Unit of Work (um commit por caso de uso) será construída sobre esta fábrica
quando os primeiros repositórios existirem — ver F2/F3 do plano.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


def criar_fabrica_de_sessoes(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
    )
