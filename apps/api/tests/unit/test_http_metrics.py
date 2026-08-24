from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.platform.observability.metrics import HttpMetricsMiddleware, router


def test_metrics_expoe_contagem_e_duracao_http() -> None:
    app = FastAPI()
    app.add_middleware(HttpMetricsMiddleware)
    app.include_router(router)

    resposta = TestClient(app).get("/metrics")

    assert resposta.status_code == 200
    assert "rfbalance_http_requests_total" in resposta.text
    assert "rfbalance_http_request_duration_seconds_sum" in resposta.text


def test_metrics_exige_token_fora_do_ambiente_local() -> None:
    app = FastAPI()
    app.state.settings = SimpleNamespace(
        app=SimpleNamespace(app_env="production", metrics_token="segredo-do-scraper")
    )
    app.include_router(router)
    client = TestClient(app)

    assert client.get("/metrics").status_code == 404
    assert client.get("/metrics", headers={"X-Metrics-Token": "incorreto"}).status_code == 404
    assert (
        client.get("/metrics", headers={"X-Metrics-Token": "segredo-do-scraper"}).status_code == 200
    )


def test_rota_desconhecida_nao_aumenta_cardinalidade_por_url() -> None:
    app = FastAPI()
    app.add_middleware(HttpMetricsMiddleware)
    app.include_router(router)
    client = TestClient(app)

    client.get("/nao-existe-1")
    client.get("/nao-existe-2")
    resposta = client.get("/metrics")

    assert 'route="__unmatched__"' in resposta.text
    assert "/nao-existe-1" not in resposta.text
    assert "/nao-existe-2" not in resposta.text
