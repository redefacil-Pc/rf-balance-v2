"""Porta: o período contábil da data de negócio aceita alteração?

Regra da seção 7.4: alterar valor ou TPS só recalcula se o período ainda estiver
aberto; período fechado exige correção compensatória, não edição destrutiva.

O dono de `accounting_periods` é o módulo `periods`, entregue na F5. Até lá o
comercial depende **desta interface**, nunca da tabela — quando o calendário
contábil existir, troca-se a implementação e nenhum caso de uso muda.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol


class PeriodGate(Protocol):
    async def garantir_aberto(self, business_date: date) -> None:
        """Levanta `PeriodClosedError` se a data cair em período já fechado."""
        ...
