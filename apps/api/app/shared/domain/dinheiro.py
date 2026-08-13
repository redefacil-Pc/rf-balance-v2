"""Valor monetário em `Decimal`, com duas casas e arredondamento explícito.

`float` não representa `0.1` exatamente: somar centavos em ponto flutuante produz
diferença de arredondamento que, em fechamento, vira divergência de comissão. O
tipo existe para que não haja aritmética monetária solta pelo código, e para que
o arredondamento aconteça em pontos nomeados (seção 4.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENTAVO = Decimal("0.01")


@dataclass(frozen=True, slots=True, order=True)
class Dinheiro:
    """Sempre normalizado em duas casas. Comparação e ordenação são por valor."""

    valor: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "valor", arredondar(self.valor))

    @classmethod
    def de(cls, bruto: Decimal | int | str) -> Dinheiro:
        """Converte a entrada externa. `float` fica de fora de propósito."""
        try:
            return cls(Decimal(bruto))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError(f"valor monetário inválido: {bruto!r}") from exc

    @classmethod
    def zero(cls) -> Dinheiro:
        return cls(Decimal("0"))

    @property
    def positivo(self) -> bool:
        return self.valor > 0

    @property
    def zerado(self) -> bool:
        return self.valor == 0

    def __add__(self, outro: Dinheiro) -> Dinheiro:
        return Dinheiro(self.valor + outro.valor)

    def __sub__(self, outro: Dinheiro) -> Dinheiro:
        return Dinheiro(self.valor - outro.valor)

    def __neg__(self) -> Dinheiro:
        return Dinheiro(-self.valor)

    def __str__(self) -> str:
        """Formato de transporte da API: string decimal, nunca `float`."""
        return f"{self.valor:.2f}"


def arredondar(valor: Decimal) -> Decimal:
    """`ROUND_HALF_UP` — o arredondamento que o financeiro usa e confere."""
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)
