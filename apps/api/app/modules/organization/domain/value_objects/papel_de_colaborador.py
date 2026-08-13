"""Papéis operacionais e regimes de contratação (seção 3.2 do blueprint).

`CONSULTOR_LIDER` do sistema atual **não** existe aqui: quem acumula funções
recebe duas linhas em `collaborator_roles` (ADR-0013).
"""

from __future__ import annotations

from enum import StrEnum


class PapelDeColaborador(StrEnum):
    CONSULTOR = "CONSULTOR"
    CONSULTOR_MEI_ESCALONADO = "CONSULTOR_MEI_ESCALONADO"
    LIDER = "LIDER"
    LIDER_MEI_GERAL = "LIDER_MEI_GERAL"
    BKO = "BKO"
    FINALIZACAO = "FINALIZACAO"
    LIDER_FINALIZACAO = "LIDER_FINALIZACAO"


class RegimeTributario(StrEnum):
    MEI = "MEI"
    CLT = "CLT"


#: Papéis que podem liderar cada tipo de vínculo (invariante "papéis precisam
#: ser compatíveis", seção 7.3).
PAPEIS_DE_LIDERANCA: dict[str, frozenset[PapelDeColaborador]] = {
    "COMERCIAL": frozenset({PapelDeColaborador.LIDER}),
    "MEI_GERAL": frozenset({PapelDeColaborador.LIDER_MEI_GERAL}),
    "FINALIZACAO": frozenset({PapelDeColaborador.LIDER_FINALIZACAO}),
}

#: Papéis que podem ser liderados em cada tipo de vínculo.
PAPEIS_LIDERAVEIS: dict[str, frozenset[PapelDeColaborador]] = {
    "COMERCIAL": frozenset(
        {PapelDeColaborador.CONSULTOR, PapelDeColaborador.CONSULTOR_MEI_ESCALONADO}
    ),
    "MEI_GERAL": frozenset(
        {
            PapelDeColaborador.CONSULTOR,
            PapelDeColaborador.CONSULTOR_MEI_ESCALONADO,
            PapelDeColaborador.LIDER,
        }
    ),
    "FINALIZACAO": frozenset({PapelDeColaborador.FINALIZACAO}),
}
