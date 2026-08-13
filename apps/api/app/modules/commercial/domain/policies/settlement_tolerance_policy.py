"""Tolerância de quitação: quando o recebido "fecha" a comissão da empresa.

O sistema atual considera quitada a proposta com diferença de até R$ 10,00 abaixo
ou R$ 100,00 acima da comissão (seção 7.4). É uma regra financeira, não uma
constante: os limites mudam por decisão do financeiro, e um recálculo precisa
saber **qual** limite valia quando a proposta foi quitada. Por isso a política é
versionada e o identificador da versão é gravado junto do resultado.

Acima do excedente tolerado o valor não vira "sobra silenciosa": a proposta é
classificada como sobrepagamento, que é uma das perguntas em aberto da seção 21 e
precisa de tratamento explícito do financeiro, não de arredondamento automático.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.shared.domain.dinheiro import Dinheiro


class ResultadoDeQuitacao(StrEnum):
    EM_ABERTO = "EM_ABERTO"
    QUITADA = "QUITADA"
    SOBREPAGAMENTO = "SOBREPAGAMENTO"


@dataclass(frozen=True, slots=True)
class SettlementTolerancePolicy:
    versao: str
    #: quanto pode faltar para a comissão e ainda assim quitar
    falta_tolerada: Dinheiro
    #: quanto pode exceder a comissão sem virar sobrepagamento
    excedente_tolerado: Dinheiro

    def classificar(self, *, esperado: Dinheiro, recebido: Dinheiro) -> ResultadoDeQuitacao:
        diferenca = recebido - esperado
        if diferenca < -self.falta_tolerada:
            return ResultadoDeQuitacao.EM_ABERTO
        if diferenca > self.excedente_tolerado:
            return ResultadoDeQuitacao.SOBREPAGAMENTO
        return ResultadoDeQuitacao.QUITADA


#: limites observados no v1 — congelados como v1 para o shadow mode da F7 poder
#: comparar proposta a proposta sem "por que deu diferente"
V1 = SettlementTolerancePolicy(
    versao="v1",
    falta_tolerada=Dinheiro.de("10.00"),
    excedente_tolerado=Dinheiro.de("100.00"),
)

_CATALOGO: dict[str, SettlementTolerancePolicy] = {V1.versao: V1}

VERSAO_VIGENTE = V1.versao


def resolver(versao: str) -> SettlementTolerancePolicy:
    """Recupera a política usada num cálculo passado. Versão desconhecida é erro:
    silenciar com a vigente reescreveria a história do fechamento."""
    politica = _CATALOGO.get(versao)
    if politica is None:
        raise ValueError(f"política de tolerância desconhecida: {versao!r}")
    return politica


def vigente() -> SettlementTolerancePolicy:
    return resolver(VERSAO_VIGENTE)
