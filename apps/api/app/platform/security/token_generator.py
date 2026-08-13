"""Geração e verificação de tokens opacos de sessão (ADR-0003).

O token em claro existe só no cookie do navegador. O banco guarda apenas o
hash — vazamento do banco não permite personificar sessão.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

TAMANHO_EM_BYTES = 32


def gerar_token() -> str:
    return secrets.token_urlsafe(TAMANHO_EM_BYTES)


def hash_do_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_iguais(token: str, hash_esperado: str) -> bool:
    """Comparação em tempo constante."""
    return hmac.compare_digest(hash_do_token(token), hash_esperado)


def hash_de_identificador(valor: str) -> str:
    """Hash de IP ou documento para log e auditoria, sem guardar o valor cru."""
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()[:32]
