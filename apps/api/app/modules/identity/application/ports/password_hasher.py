"""Porta de hashing de senha.

O domínio não conhece Argon2 nem bcrypt — só a capacidade de verificar e gerar.
"""

from __future__ import annotations

from typing import Protocol


class PasswordHasher(Protocol):
    def gerar(self, senha: str) -> str: ...

    def verificar(self, senha: str, hash_armazenado: str) -> bool: ...

    def precisa_reforcar(self, hash_armazenado: str) -> bool:
        """True quando o hash foi gerado com custo inferior ao atual."""
        ...
