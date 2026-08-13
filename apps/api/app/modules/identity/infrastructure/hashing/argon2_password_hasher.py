"""Hashing de senha com Argon2id (seção 13.1)."""

from __future__ import annotations

from argon2 import PasswordHasher as Argon2
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class Argon2PasswordHasher:
    """Custo revisável: alterar os parâmetros aqui faz `precisa_reforcar` pedir
    o reprocessamento do hash no próximo login bem-sucedido."""

    __slots__ = ("_argon2",)

    def __init__(self) -> None:
        self._argon2 = Argon2(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32)

    def gerar(self, senha: str) -> str:
        return self._argon2.hash(senha)

    def verificar(self, senha: str, hash_armazenado: str) -> bool:
        try:
            return self._argon2.verify(hash_armazenado, senha)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def precisa_reforcar(self, hash_armazenado: str) -> bool:
        try:
            return self._argon2.check_needs_rehash(hash_armazenado)
        except InvalidHashError:
            return True
