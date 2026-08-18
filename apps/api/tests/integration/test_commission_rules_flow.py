from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from app.platform.config.security import CSRF_COOKIE, CSRF_HEADER

pytestmark = pytest.mark.integration


def _regras() -> list[dict[str, str | None]]:
    resultado: list[dict[str, str | None]] = []
    for minimo, maximo, percentual in (
        ("0", "25", "6"),
        ("25", "30", "8"),
        ("30", "35", "10"),
        ("35", None, "12"),
    ):
        resultado.append(
            {
                "tax_regime": "MEI",
                "tps_min": minimo,
                "tps_max": maximo,
                "percentage": percentual,
            }
        )
    return resultado


@pytest.fixture
async def api(cliente: AsyncClient, admin_semeado: dict[str, str]) -> AsyncClient:
    await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )
    return cliente


def _csrf(api: AsyncClient) -> dict[str, str]:
    return {CSRF_HEADER: api.cookies[CSRF_COOKIE]}


async def test_lista_a_versao_inicial(api: AsyncClient) -> None:
    resposta = await api.get("/api/v1/commission-rule-sets")
    assert resposta.status_code == 200
    inicial = resposta.json()[0]
    assert inicial["version"] == "2026.1"
    assert inicial["status"] == "ACTIVE"
    assert len(inicial["rules"]) == 4
    assert {item["tax_regime"] for item in inicial["rules"]} == {"MEI"}


async def test_cria_e_ativa_nova_versao_sem_alterar_a_anterior(api: AsyncClient) -> None:
    corpo: dict[str, Any] = {
        "version": "2099.1",
        "name": "Nova tabela padrão",
        "valid_from": "2099-01-01",
        "reason": "Revisão anual aprovada",
        "rules": _regras(),
    }
    criada = await api.post("/api/v1/commission-rule-sets", json=corpo, headers=_csrf(api))
    assert criada.status_code == 201, criada.text
    assert criada.json()["status"] == "DRAFT"

    ativada = await api.post(
        f"/api/v1/commission-rule-sets/{criada.json()['id']}/activation",
        json={"reason": "Publicação autorizada"},
        headers=_csrf(api),
    )
    assert ativada.status_code == 200, ativada.text
    assert ativada.json()["status"] == "ACTIVE"

    listagem = (await api.get("/api/v1/commission-rule-sets")).json()
    anterior = next(item for item in listagem if item["version"] == "2026.1")
    assert anterior["valid_to"] == "2098-12-31"
    assert anterior["rules"][0]["percentage"] == "6.000000"


async def test_rejeita_faixas_com_lacuna(api: AsyncClient) -> None:
    regras = _regras()
    regras[1]["tps_min"] = "26"
    resposta = await api.post(
        "/api/v1/commission-rule-sets",
        json={
            "version": "2099.invalida",
            "name": "Tabela com lacuna",
            "valid_from": "2099-01-01",
            "reason": "Teste de validação",
            "rules": regras,
        },
        headers=_csrf(api),
    )
    assert resposta.status_code == 422
    assert resposta.json()["type"].endswith("invalid-commission-rule-configuration")


async def test_rejeita_nova_tabela_do_consultor_clt(api: AsyncClient) -> None:
    regras = _regras()
    regras[0]["tax_regime"] = "CLT"
    resposta = await api.post(
        "/api/v1/commission-rule-sets",
        json={
            "version": "2099.clt",
            "name": "Tabela CLT obsoleta",
            "valid_from": "2099-01-01",
            "reason": "Teste da retirada do consultor CLT",
            "rules": regras,
        },
        headers=_csrf(api),
    )
    assert resposta.status_code == 422
