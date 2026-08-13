"""Implementação provisória da porta de período: tudo aberto.

Enquanto `accounting_periods` não existe (F5), não há período fechado no sistema
— e um gate que sempre nega ou que consulta uma tabela inexistente seria pior que
este, que é explícito sobre o que ainda não foi construído.

Quando a F5 entregar o calendário contábil, esta classe sai e a implementação de
`periods` entra no lugar. O ponto de troca é `api/dependencies.py`; nenhum caso
de uso precisa mudar.
"""

from __future__ import annotations

from datetime import date


class OpenPeriodGate:
    __slots__ = ()

    async def garantir_aberto(self, business_date: date) -> None:
        return None
