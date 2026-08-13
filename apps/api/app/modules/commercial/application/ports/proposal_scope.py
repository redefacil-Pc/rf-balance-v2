"""Escopo de leitura de propostas: o recorte de "o que é meu".

Permissão e escopo respondem perguntas diferentes. `proposals:read` diz *se* a
pessoa pode ler proposta; o escopo diz *quais*. Sem o segundo, um consultor com
a permissão legítima enxerga a carteira de todos os colegas, com nome de
cliente.

O escopo nasce do papel operacional vigente **na data**, não do perfil de
acesso: quem lidera hoje pode não ter liderado em março, e é a equipe de março
que explica uma proposta de março.

Fail closed por construção: um escopo sem `irrestrito` e sem id nenhum não
devolve nada. Conta sem vínculo com colaborador não é "vê tudo por omissão" — é
"não vê nada até alguém vincular".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EscopoDePropostas:
    #: administração e financeiro leem a base inteira
    irrestrito: bool = False
    #: participação na proposta — como consultor, BKO **ou** finalizador.
    #: Uma pessoa de finalização não entra como consultor; cobrir só aquela
    #: coluna a deixaria sem enxergar o próprio trabalho.
    colaboradores: tuple[int, ...] = ()
    #: usuários que registraram a proposta (`created_by`), para a retaguarda
    #: acompanhar o que ela mesma cadastrou
    registradores: tuple[int, ...] = ()

    @property
    def vazio(self) -> bool:
        return not (self.irrestrito or self.colaboradores or self.registradores)

    @staticmethod
    def total() -> EscopoDePropostas:
        return EscopoDePropostas(irrestrito=True)


class ProposalScopeResolver(Protocol):
    """Traduz quem está logado no recorte que ele pode ler.

    Recebe primitivos, não a entidade de usuário: o escopo depende de papéis e
    de vigência, não de como a identidade é modelada.
    """

    async def resolver(
        self, *, user_id: int, papeis: frozenset[str], referencia: date
    ) -> EscopoDePropostas: ...
