from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.platform.config.security import CSRF_COOKIE, CSRF_HEADER

pytestmark = pytest.mark.integration


@pytest.fixture
async def api(cliente: AsyncClient, admin_semeado: dict[str, str]) -> AsyncClient:
    await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )
    return cliente


def _csrf(api: AsyncClient) -> dict[str, str]:
    return {CSRF_HEADER: api.cookies[CSRF_COOKIE]}


async def test_lista_as_cinco_estrategias_documentadas(api: AsyncClient) -> None:
    resposta = await api.get("/api/v1/commission-strategy-configs")
    assert resposta.status_code == 200
    configs = resposta.json()
    assert {item["strategy"] for item in configs} == {
        "SCALED_CONSULTANT",
        "COMMERCIAL_LEADER",
        "GENERAL_MEI_LEADER",
        "FINALIZER",
        "FINALIZATION_LEADER",
    }
    escalonado = next(item for item in configs if item["strategy"] == "SCALED_CONSULTANT")
    assert escalonado["config"]["production_ranges"][2]["percentages"] == [
        "11.5",
        "9.5",
        "7.5",
        "5.5",
    ]


async def test_cria_e_ativa_correcao_versionada(api: AsyncClient) -> None:
    criada = await api.post(
        "/api/v1/commission-strategy-configs",
        json={
            "strategy": "COMMERCIAL_LEADER",
            "version": "2099.1",
            "name": "Líder comercial corrigido",
            "valid_from": "2099-01-01",
            "reason": "Correção aprovada",
            "config": {
                "mei_min_tps": "26.5",
                "mei_percentage": "3.25",
                "clt_percentage": "0",
            },
        },
        headers=_csrf(api),
    )
    assert criada.status_code == 201, criada.text
    assert criada.json()["status"] == "DRAFT"

    ativada = await api.post(
        f"/api/v1/commission-strategy-configs/{criada.json()['id']}/activation",
        json={"reason": "Publicação autorizada"},
        headers=_csrf(api),
    )
    assert ativada.status_code == 200, ativada.text
    assert ativada.json()["status"] == "ACTIVE"

    configs = (await api.get("/api/v1/commission-strategy-configs")).json()
    anterior = next(
        item
        for item in configs
        if item["strategy"] == "COMMERCIAL_LEADER" and item["version"] == "2026.1"
    )
    assert anterior["valid_to"] == "2098-12-31"


async def test_rejeita_faixa_escalonada_com_lacuna(api: AsyncClient) -> None:
    resposta = await api.post(
        "/api/v1/commission-strategy-configs",
        json={
            "strategy": "SCALED_CONSULTANT",
            "version": "2099.invalida",
            "name": "Faixas inválidas",
            "valid_from": "2099-01-01",
            "reason": "Teste de validação",
            "config": {
                "display_mode": "WEEKLY",
                "production_ranges": [
                    {"min": "0", "max": "75000", "percentages": ["8", "6", "4", "2"]},
                    {
                        "min": "76000",
                        "max": None,
                        "percentages": ["11.5", "9.5", "7.5", "5.5"],
                    },
                ],
            },
        },
        headers=_csrf(api),
    )
    assert resposta.status_code == 422
    assert resposta.json()["type"].endswith("invalid-commission-rule-configuration")


async def test_rejeita_escalonado_sem_faixas_tps(api: AsyncClient) -> None:
    resposta = await api.post(
        "/api/v1/commission-strategy-configs",
        json={
            "strategy": "SCALED_CONSULTANT",
            "version": "2099.sem-tps",
            "name": "Escalonado incompleto",
            "valid_from": "2099-01-01",
            "reason": "Teste de validação",
            "config": {
                "display_mode": "WEEKLY",
                "production_ranges": [
                    {"min": "0", "max": None, "percentages": ["8", "6", "4", "2"]}
                ],
            },
        },
        headers=_csrf(api),
    )
    assert resposta.status_code == 422
    assert resposta.json()["type"].endswith("invalid-commission-rule-configuration")
