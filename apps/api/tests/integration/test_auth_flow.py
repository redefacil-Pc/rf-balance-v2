"""Fluxo de autenticação ponta a ponta (seções 16.3 e 16.4 do blueprint).

Cobre: sem sessão -> 401, credencial inválida -> 401 genérico, throttle -> 429,
CSRF ausente -> 403, rotação de token, replay do token antigo -> 401, logout
idempotente e trilha de auditoria gravada.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.platform.config.security import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine

pytestmark = pytest.mark.integration


async def _acoes_auditadas() -> list[str]:
    engine = criar_engine(get_settings().database)
    try:
        async with engine.connect() as conexao:
            linhas = await conexao.execute(text("SELECT action FROM audit_events ORDER BY id"))
            return [str(linha[0]) for linha in linhas]
    finally:
        await engine.dispose()


async def test_login_emite_os_dois_cookies_e_retorna_permissoes(
    cliente: AsyncClient, admin_semeado: dict[str, str]
) -> None:
    resposta = await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["email"] == admin_semeado["email"]
    assert "ADMIN" in corpo["roles"]
    assert "settlements:approve" in corpo["permissions"]
    assert SESSION_COOKIE in resposta.cookies
    assert CSRF_COOKIE in resposta.cookies


async def test_me_sem_sessao_retorna_401(cliente: AsyncClient) -> None:
    resposta = await cliente.get("/api/v1/auth/me")

    assert resposta.status_code == 401
    assert resposta.headers["content-type"].startswith("application/problem+json")
    assert resposta.json()["correlation_id"]


async def test_credencial_invalida_nao_revela_existencia_da_conta(
    cliente: AsyncClient, admin_semeado: dict[str, str]
) -> None:
    inexistente = await cliente.post(
        "/api/v1/auth/login",
        json={"email": "ninguem@rfbalance.local", "password": "qualquer-senha-longa"},
    )
    senha_errada = await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": "senha-errada-mas-longa"},
    )

    assert inexistente.status_code == senha_errada.status_code == 401
    assert inexistente.json()["type"] == senha_errada.json()["type"]
    assert inexistente.json()["detail"] == senha_errada.json()["detail"]


async def test_tentativas_excedidas_retornam_429(
    cliente: AsyncClient, admin_semeado: dict[str, str]
) -> None:
    limite = get_settings().security.login_max_attempts

    for _ in range(limite):
        erro = await cliente.post(
            "/api/v1/auth/login",
            json={"email": admin_semeado["email"], "password": "senha-errada-mas-longa"},
        )
        assert erro.status_code == 401

    bloqueado = await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )

    assert bloqueado.status_code == 429
    assert bloqueado.json()["type"].endswith("too-many-attempts")


async def test_refresh_sem_csrf_retorna_403(
    cliente: AsyncClient, admin_semeado: dict[str, str]
) -> None:
    await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )

    resposta = await cliente.post("/api/v1/auth/refresh")

    assert resposta.status_code == 403
    assert resposta.json()["type"].endswith("csrf-invalid")


async def test_refresh_rotaciona_token_e_invalida_o_anterior(
    cliente: AsyncClient, admin_semeado: dict[str, str]
) -> None:
    await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )
    token_antigo = cliente.cookies[SESSION_COOKIE]
    csrf = cliente.cookies[CSRF_COOKIE]

    renovacao = await cliente.post("/api/v1/auth/refresh", headers={CSRF_HEADER: csrf})
    token_novo = cliente.cookies[SESSION_COOKIE]

    assert renovacao.status_code == 204
    assert token_novo != token_antigo
    assert (await cliente.get("/api/v1/auth/me")).status_code == 200

    # replay: o token anterior não vale mais
    cliente.cookies.set(SESSION_COOKIE, token_antigo)
    assert (await cliente.get("/api/v1/auth/me")).status_code == 401


async def test_logout_revoga_a_sessao_e_e_idempotente(
    cliente: AsyncClient, admin_semeado: dict[str, str]
) -> None:
    await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )
    csrf = cliente.cookies[CSRF_COOKIE]

    primeiro = await cliente.post("/api/v1/auth/logout", headers={CSRF_HEADER: csrf})
    assert primeiro.status_code == 204
    assert (await cliente.get("/api/v1/auth/me")).status_code == 401

    # O handler é idempotente: repetir o logout com a sessão já encerrada não é
    # erro. O cookie CSRF é reposto porque o logout anterior o apagou — e a
    # proteção CSRF continua valendo no logout, para não permitirem encerrar a
    # sessão de um terceiro.
    cliente.cookies.set(CSRF_COOKIE, csrf)
    segundo = await cliente.post("/api/v1/auth/logout", headers={CSRF_HEADER: csrf})
    assert segundo.status_code == 204


async def test_logout_sem_csrf_e_recusado(
    cliente: AsyncClient, admin_semeado: dict[str, str]
) -> None:
    """Encerrar sessão também é mutação: exige CSRF como qualquer POST."""
    await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )

    resposta = await cliente.post("/api/v1/auth/logout")

    assert resposta.status_code == 403
    assert (await cliente.get("/api/v1/auth/me")).status_code == 200


async def test_trilha_de_auditoria_registra_sucesso_e_recusa(
    cliente: AsyncClient, admin_semeado: dict[str, str]
) -> None:
    await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": "senha-errada-mas-longa"},
    )
    await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )

    acoes = await _acoes_auditadas()

    assert "session.denied" in acoes
    assert "session.opened" in acoes
