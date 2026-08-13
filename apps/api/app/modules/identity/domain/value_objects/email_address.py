"""E-mail normalizado.

A normalização acontece uma vez, na construção. A unicidade é do banco; este
value object garante que o valor comparado seja sempre o mesmo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_FORMATO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TAMANHO_MAXIMO = 320


@dataclass(frozen=True, slots=True)
class EmailAddress:
    valor: str

    def __post_init__(self) -> None:
        if not _FORMATO.match(self.valor):
            raise ValueError(f"e-mail inválido: {self.valor}")

    @classmethod
    def normalizar(cls, bruto: str) -> EmailAddress:
        normalizado = bruto.strip().lower()
        if len(normalizado) > TAMANHO_MAXIMO:
            raise ValueError("e-mail excede o tamanho máximo")
        return cls(normalizado)

    def __str__(self) -> str:
        return self.valor
