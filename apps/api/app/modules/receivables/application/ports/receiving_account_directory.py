"""Porta: a conta de recebimento escolhida existe e está disponível?

O catálogo de contas pertence a `organization`. `receivables` só precisa saber se
a conta que o operador escolheu pode ser usada — então pergunta por aqui, em vez
de importar o model alheio ou fazer `select` cruzado.

A implementação entra pela composição, como no `ReceiptRecognizer`.
"""

from __future__ import annotations

from typing import Protocol


class ReceivingAccountDirectory(Protocol):
    async def esta_disponivel(self, account_id: int) -> bool:
        """Verdadeiro quando a conta existe e está ativa.

        Conta desativada recusa lançamento novo, mas continua válida nos
        recebimentos que já apontam para ela — desativar não reescreve história.
        """
        ...
