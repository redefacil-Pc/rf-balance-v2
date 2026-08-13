"""Paginação por cursor (seção 9.1).

`OFFSET` alto obriga o banco a percorrer e descartar tudo o que veio antes —
é uma das causas clássicas de listagem que fica lenta conforme a base cresce.
O cursor é opaco para o cliente: um par (ordenação, id) codificado em base64.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from app.platform.errors.domain_error import DomainError

T = TypeVar("T")

LIMITE_PADRAO = 25
LIMITE_MAXIMO = 200


class CursorInvalidoError(DomainError):
    status = 422
    code = "cursor-invalido"
    title = "Cursor inválido"


@dataclass(frozen=True, slots=True)
class Cursor:
    """Última posição lida. `chave` é o valor da coluna de ordenação."""

    chave: str
    id: int

    def codificar(self) -> str:
        bruto = json.dumps({"k": self.chave, "i": self.id}, separators=(",", ":"))
        return base64.urlsafe_b64encode(bruto.encode("utf-8")).decode("ascii")

    @classmethod
    def decodificar(cls, texto: str) -> Cursor:
        try:
            dados = json.loads(base64.urlsafe_b64decode(texto.encode("ascii")))
            return cls(chave=str(dados["k"]), id=int(dados["i"]))
        except Exception as exc:
            raise CursorInvalidoError("O cursor de paginação é inválido.") from exc


@dataclass(frozen=True, slots=True)
class Pagina(Generic[T]):
    itens: list[T]
    proximo_cursor: str | None

    def para_dicionario(self, serializar: Any) -> dict[str, object]:
        return {
            "items": [serializar(item) for item in self.itens],
            "next_cursor": self.proximo_cursor,
        }


def normalizar_limite(limite: int | None) -> int:
    if limite is None:
        return LIMITE_PADRAO
    return max(1, min(limite, LIMITE_MAXIMO))
