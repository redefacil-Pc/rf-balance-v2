"""Política de senha.

Mínimo de 12 caracteres, seguindo a orientação atual de priorizar comprimento
sobre composição obrigatória. Sem exigência de troca periódica.
"""

from __future__ import annotations

from app.modules.identity.domain.errors import WeakPasswordError

TAMANHO_MINIMO = 12
TAMANHO_MAXIMO = 128

_SENHAS_PROIBIDAS = frozenset({"senha", "password", "123456789012", "rfbalance", "administrador"})


def validar(senha: str) -> None:
    if len(senha) < TAMANHO_MINIMO:
        raise WeakPasswordError(f"A senha deve ter ao menos {TAMANHO_MINIMO} caracteres.")
    if len(senha) > TAMANHO_MAXIMO:
        raise WeakPasswordError(f"A senha deve ter no máximo {TAMANHO_MAXIMO} caracteres.")
    if senha.strip().lower() in _SENHAS_PROIBIDAS:
        raise WeakPasswordError("Escolha uma senha menos previsível.")
