"""Cifragem de PII e hash determinístico para busca (ADR-0012).

Cada valor sensível é guardado em dois campos: o cifrado, que é o dado, e o
hash, que sustenta índice único e busca exata. Hash de CPF **sem pepper** não
protege nada — 11 dígitos são enumeráveis — por isso o HMAC.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PREFIXO_DA_VERSAO = "v1"
TAMANHO_DO_NONCE = 12


class PiiCipherError(RuntimeError):
    """Falha de configuração ou de integridade na cifragem de PII."""


class PiiCipher:
    __slots__ = ("_aesgcm", "_pepper")

    def __init__(self, chave: bytes, pepper: bytes) -> None:
        if len(chave) != 32:
            raise PiiCipherError("PII_ENCRYPTION_KEY deve ter 32 bytes (256 bits)")
        if len(pepper) < 16:
            raise PiiCipherError("PII_HASH_PEPPER deve ter ao menos 16 bytes")
        self._aesgcm = AESGCM(chave)
        self._pepper = pepper

    def cifrar(self, valor: str) -> str:
        nonce = os.urandom(TAMANHO_DO_NONCE)
        cifrado = self._aesgcm.encrypt(nonce, valor.encode("utf-8"), None)
        return f"{PREFIXO_DA_VERSAO}:{base64.b64encode(nonce + cifrado).decode('ascii')}"

    def decifrar(self, armazenado: str) -> str:
        versao, _, corpo = armazenado.partition(":")
        if versao != PREFIXO_DA_VERSAO or not corpo:
            raise PiiCipherError(f"formato de PII não reconhecido: versão {versao!r}")

        bruto = base64.b64decode(corpo)
        nonce, cifrado = bruto[:TAMANHO_DO_NONCE], bruto[TAMANHO_DO_NONCE:]
        try:
            return self._aesgcm.decrypt(nonce, cifrado, None).decode("utf-8")
        except InvalidTag as exc:
            raise PiiCipherError("PII adulterada ou chave incorreta") from exc

    def hash_de_busca(self, valor_normalizado: str) -> str:
        """Determinístico: sustenta índice único e busca exata, nunca ordenação."""
        return hmac.new(self._pepper, valor_normalizado.encode("utf-8"), hashlib.sha256).hexdigest()


def criar(chave_base64: str, pepper: str) -> PiiCipher:
    try:
        chave = base64.b64decode(chave_base64, validate=True)
    except Exception as exc:
        raise PiiCipherError("PII_ENCRYPTION_KEY precisa ser base64 de 32 bytes") from exc
    return PiiCipher(chave, pepper.encode("utf-8"))
