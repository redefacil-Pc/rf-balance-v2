"""Situação de aprovação da proposta — o fluxo cadastro → financeiro.

Dimensão **separada** do status financeiro (`StatusDaProposta`): uma coisa é a
proposta estar quitada ou em aberto perante o caixa; outra é ela ter passado pelo
crivo do financeiro para existir no sistema. Misturar as duas num enum só criaria
estados impossíveis (rejeitada-e-paga) e obrigaria a F3 a conhecer o fluxo de
cadastro.

O ciclo: quem cadastra (finalização/cobrança) monta a proposta em rascunho,
anexa o comprovante do pagamento do cliente e envia. O financeiro aprova — e só
então a proposta passa a valer para recebimento e comissão — ou rejeita com
motivo, devolvendo para correção e reenvio. O histórico de idas e vindas fica na
auditoria, não em coluna.
"""

from __future__ import annotations

from enum import StrEnum


class SituacaoDeAprovacao(StrEnum):
    #: em elaboração por quem cadastra; editável e com anexos livres
    DRAFT = "DRAFT"
    #: enviada ao financeiro; travada para edição até a decisão
    SUBMITTED = "SUBMITTED"
    #: aceita pelo financeiro; é o que "existe" para recebimento e comissão
    APPROVED = "APPROVED"
    #: devolvida com motivo; editável de novo para correção e reenvio
    REJECTED = "REJECTED"


TRANSICOES: dict[SituacaoDeAprovacao, frozenset[SituacaoDeAprovacao]] = {
    SituacaoDeAprovacao.DRAFT: frozenset({SituacaoDeAprovacao.SUBMITTED}),
    SituacaoDeAprovacao.SUBMITTED: frozenset(
        {SituacaoDeAprovacao.APPROVED, SituacaoDeAprovacao.REJECTED}
    ),
    #: rejeitada volta ao circuito por reenvio, nunca vira aprovada por fora
    SituacaoDeAprovacao.REJECTED: frozenset({SituacaoDeAprovacao.SUBMITTED}),
    #: aprovação é terminal — desfazer aprovação é cancelar a proposta
    SituacaoDeAprovacao.APPROVED: frozenset(),
}


def permite(origem: SituacaoDeAprovacao, destino: SituacaoDeAprovacao) -> bool:
    return destino in TRANSICOES[origem]


#: situações em que quem cadastra ainda pode editar e mexer nos anexos
EDITAVEIS = frozenset({SituacaoDeAprovacao.DRAFT, SituacaoDeAprovacao.REJECTED})
