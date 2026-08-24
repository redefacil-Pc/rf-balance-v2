"""Porta: reconhecer os recebimentos declarados quando a proposta é aprovada.

O fluxo é um só: a Finalização lança a proposta **com os valores recebidos e os
comprovantes**, e o Financeiro confere no extrato e aprova. A aprovação é o
momento em que o dinheiro passa a valer — não existe uma segunda decisão sobre o
mesmo valor.

Por isso `commercial` avisa, e não pergunta: quem sabe somar recebimento é
`receivables`. Mesmo desenho do `PeriodGate` — a interface mora aqui, a
implementação entra pela composição.

Roda **dentro da transação da decisão**: aprovar a proposta e reconhecer o valor
são o mesmo fato. Em dois commits, uma falha no segundo deixaria proposta
aprovada com saldo zerado, e ninguém saberia que faltou.
"""

from __future__ import annotations

from typing import Protocol

from app.shared.domain.dinheiro import Dinheiro


class ReceiptRecognizer(Protocol):
    async def contar_declarados(self, proposal_id: int) -> int:
        """Quantidade de recebimentos com comprovante aguardando reconhecimento."""
        ...

    async def reconhecer(self, proposal_id: int, *, ator: int | None) -> Dinheiro:
        """Reconhece os recebimentos declarados e devolve o total que passa a
        valer para a proposta — já descontando o que foi estornado."""
        ...

    async def foi_declarado_por(self, proposal_id: int, actor: int) -> bool:
        """Indica se o aprovador participou da declaração financeira da proposta."""
        ...
