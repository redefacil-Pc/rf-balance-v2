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
