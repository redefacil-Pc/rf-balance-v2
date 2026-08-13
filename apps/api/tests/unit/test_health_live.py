"""`/health/live` responde sem tocar em nenhuma dependência."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.platform.http.health_router import router


def _app_isolado() -> FastAPI:
    """App sem lifespan: se a rota precisasse de banco, Redis ou storage, falharia."""
    app = FastAPI()
    app.include_router(router)
    return app


def test_live_retorna_alive() -> None:
    resposta = TestClient(_app_isolado()).get("/health/live")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "alive"}
