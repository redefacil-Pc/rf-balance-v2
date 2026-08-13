"""Proteção CSRF por double submit (ADR-0003).

O cookie `rfb_csrf` é legível pelo JavaScript e precisa ser reenviado no header
`X-CSRF-Token`. Em métodos não seguros, divergência ou ausência é 403.
"""

from __future__ import annotations

import hmac

from fastapi import Request

from app.platform.config.security import CSRF_COOKIE, CSRF_HEADER
from app.platform.errors.domain_error import PermissionDeniedError

METODOS_SEGUROS = frozenset({"GET", "HEAD", "OPTIONS"})

# O login é a única exceção possível: quem ainda não tem sessão também não tem
# cookie CSRF para reenviar. Fica protegido por outros controles — rate limit por
# e-mail e IP, `SameSite=Lax` no cookie emitido e CORS com allowlist exata.
ROTAS_ISENTAS = frozenset({"/api/v1/auth/login"})


class CsrfError(PermissionDeniedError):
    code = "csrf-invalid"
    title = "Token CSRF inválido"


def guard(request: Request) -> None:
    """Dependência global: protege **toda** rota de método não seguro.

    Registrada em `criar_app`. Não depender de `current_user` para isso — rota
    que não resolve usuário, como o refresh, ficaria descoberta.
    """
    if request.url.path in ROTAS_ISENTAS:
        return
    validar(request)


def validar(request: Request) -> None:
    if request.method in METODOS_SEGUROS:
        return

    do_cookie = request.cookies.get(CSRF_COOKIE, "")
    do_header = request.headers.get(CSRF_HEADER, "")

    if not do_cookie or not do_header:
        raise CsrfError("Requisição sem token CSRF.")
    if not hmac.compare_digest(do_cookie, do_header):
        raise CsrfError("Token CSRF divergente.")
