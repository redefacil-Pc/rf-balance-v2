"""Resolve o escopo de propostas a partir do perfil de acesso e da equipe.

Este é o ponto de tradução entre três módulos: `identity` diz o perfil,
`organization` diz quem é a pessoa, `teams` diz quem ela lidera. O `commercial`
consome só a porta e não conhece nenhum dos três.

Regra por perfil:

- **ADMIN / FINANCEIRO** — base inteira. Conciliação e aprovação não funcionam
  com recorte.
- **LIDERANCA** — a própria participação mais a da equipe vigente na data.
- **CONSULTOR** — só a própria participação.
- **OPERACIONAL** — o que a própria conta registrou (`created_by`). Retaguarda
  cadastra proposta de terceiros e precisa achar o que digitou para corrigir e
  reenviar.

Perfis acumulam por união: quem é liderança e operacional enxerga os dois
recortes.
"""

from __future__ import annotations

from datetime import date

from app.modules.commercial.application.ports.proposal_scope import EscopoDePropostas
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.modules.teams.infrastructure.repositories.sql_team_assignment_repository import (
    SqlTeamAssignmentRepository,
)

#: perfis que leem a base inteira
IRRESTRITOS = frozenset({"ADMIN", "FINANCEIRO"})
#: perfis cujo recorte é a própria participação
PROPRIA_PARTICIPACAO = frozenset({"CONSULTOR", "LIDERANCA"})


class RbacProposalScope:
    __slots__ = ("_colaboradores", "_vinculos")

    def __init__(
        self,
        colaboradores: SqlCollaboratorRepository,
        vinculos: SqlTeamAssignmentRepository,
    ) -> None:
        self._colaboradores = colaboradores
        self._vinculos = vinculos

    async def resolver(
        self, *, user_id: int, papeis: frozenset[str], referencia: date
    ) -> EscopoDePropostas:
        if papeis & IRRESTRITOS:
            return EscopoDePropostas.total()

        registradores = (user_id,) if "OPERACIONAL" in papeis else ()
        colaboradores = await self._participacao(user_id, papeis, referencia)

        return EscopoDePropostas(colaboradores=colaboradores, registradores=registradores)

    async def _participacao(
        self, user_id: int, papeis: frozenset[str], referencia: date
    ) -> tuple[int, ...]:
        if not papeis & PROPRIA_PARTICIPACAO:
            return ()

        # sem vínculo com colaborador não há "meu": devolve vazio em vez de
        # tudo, para a falta de cadastro nunca virar liberação
        eu = await self._colaboradores.colaborador_da_conta(user_id)
        if eu is None:
            return ()

        if "LIDERANCA" not in papeis:
            return (eu.id,)

        equipe = await self._vinculos.equipe_do_lider_em(leader_id=eu.id, referencia=referencia)
        # O líder não realiza venda nova, mas permanece no recorte para que
        # propostas históricas continuem auditáveis.
        return tuple({eu.id, *(v.consultant_id for v in equipe)})
