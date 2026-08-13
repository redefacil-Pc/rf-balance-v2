"""Criação do engine assíncrono do SQLAlchemy.

O dimensionamento do pool é monitorado — pool saturado é causa comum de
latência percebida como "banco lento".
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.platform.config.database import DatabaseSettings


def criar_engine(settings: DatabaseSettings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_recycle=settings.database_pool_recycle,
        pool_pre_ping=True,
        echo=settings.database_echo,
        future=True,
    )
