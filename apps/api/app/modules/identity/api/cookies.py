"""Escrita e remoção dos cookies de sessão (ADR-0003).

Único lugar do código que decide flags de cookie. `HttpOnly` no cookie de
sessão; o de CSRF é legível por design, para o frontend reenviar no header.
"""

from __future__ import annotations

from fastapi import Response

from app.platform.config.security import CSRF_COOKIE, SESSION_COOKIE, SecuritySettings


def definir(response: Response, *, token: str, csrf_token: str, settings: SecuritySettings) -> None:
    dominio = settings.cookie_domain or None

    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        domain=dominio,
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        max_age=settings.session_ttl,
        httponly=False,  # o JavaScript precisa ler para reenviar no header
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        domain=dominio,
    )


def limpar(response: Response, *, settings: SecuritySettings) -> None:
    dominio = settings.cookie_domain or None
    for nome in (SESSION_COOKIE, CSRF_COOKIE):
        response.delete_cookie(nome, path="/", domain=dominio)
