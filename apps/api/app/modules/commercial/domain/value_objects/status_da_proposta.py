"""Estados da proposta e as transições permitidas (seção 6.7).

Estado não é rótulo livre: cada transição tem origem declarada. Um `UPDATE
proposals SET status = ...` em qualquer outro ponto do sistema é bug, não atalho.
"""

from __future__ import annotations

from enum import StrEnum


class StatusDaProposta(StrEnum):
    #: nenhum recebimento elegível
    OPEN = "OPEN"
    #: recebido algo, ainda abaixo da comissão da empresa
    PARTIALLY_PAID = "PARTIALLY_PAID"
    #: quitada dentro da tolerância
    PAID = "PAID"
    #: sem efeito financeiro; não volta atrás
    CANCELLED = "CANCELLED"


#: estorno reabre a proposta, por isso PAID volta para PARTIALLY_PAID e OPEN
TRANSICOES: dict[StatusDaProposta, frozenset[StatusDaProposta]] = {
    StatusDaProposta.OPEN: frozenset(
        {StatusDaProposta.PARTIALLY_PAID, StatusDaProposta.PAID, StatusDaProposta.CANCELLED}
    ),
    StatusDaProposta.PARTIALLY_PAID: frozenset(
        {StatusDaProposta.OPEN, StatusDaProposta.PAID, StatusDaProposta.CANCELLED}
    ),
    StatusDaProposta.PAID: frozenset(
        {StatusDaProposta.OPEN, StatusDaProposta.PARTIALLY_PAID, StatusDaProposta.CANCELLED}
    ),
    #: cancelamento é terminal
    StatusDaProposta.CANCELLED: frozenset(),
}


def permite(origem: StatusDaProposta, destino: StatusDaProposta) -> bool:
    return destino is origem or destino in TRANSICOES[origem]
