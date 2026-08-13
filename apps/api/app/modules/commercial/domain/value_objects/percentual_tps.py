"""TPS: o percentual da operação que fica como comissão da empresa (seção 7.4).

O cálculo mora aqui e em nenhum outro lugar. Se `operacao * tps / 100` aparecer
numa query, num relatório ou no frontend, existem duas verdades para o mesmo
número — que é exatamente a divergência que a reconstrução precisa eliminar.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.shared.domain.dinheiro import Dinheiro

MINIMO = Decimal("0")
MAXIMO = Decimal("100")
#: DECIMAL(9,6) na coluna — seis casas comportam frações de ponto percentual
PRECISAO = Decimal("0.000001")
CEM = Decimal("100")


@dataclass(frozen=True, slots=True, order=True)
class PercentualTps:
    valor: Decimal

    def __post_init__(self) -> None:
        normalizado = self.valor.quantize(PRECISAO, rounding=ROUND_HALF_UP)
        if not MINIMO <= normalizado <= MAXIMO:
            raise ValueError(f"TPS deve estar entre 0 e 100, recebido {self.valor}")
        object.__setattr__(self, "valor", normalizado)

    @classmethod
    def de(cls, bruto: Decimal | int | str) -> PercentualTps:
        try:
            return cls(Decimal(bruto))
        except (InvalidOperation, TypeError) as exc:
            raise ValueError(f"TPS inválido: {bruto!r}") from exc

    def aplicar_sobre(self, operacao: Dinheiro) -> Dinheiro:
        """Comissão da empresa. Arredonda uma única vez, no fim da conta."""
        return Dinheiro(operacao.valor * self.valor / CEM)

    def __str__(self) -> str:
        return f"{self.valor:.6f}"
