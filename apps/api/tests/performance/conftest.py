"""Aplicação real sobre a massa volumétrica preparada pelo job de CI."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRET_KEY", "performance-secret-key-com-mais-de-32-caracteres")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/8")
os.environ["COOKIE_SECURE"] = "true"


@pytest.fixture
async def performance_client() -> AsyncIterator[AsyncClient]:
    from asgi_lifespan import LifespanManager

    from app.main import criar_app
    from app.platform.db.seed_volumetric import PERFORMANCE_PASSWORD

    app: Any = criar_app()
    async with (
        LifespanManager(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="https://performance",
        ) as client,
    ):
        login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@rfbalance.local",
                "password": PERFORMANCE_PASSWORD,
            },
        )
        assert login.status_code == 200, login.text
        yield client
