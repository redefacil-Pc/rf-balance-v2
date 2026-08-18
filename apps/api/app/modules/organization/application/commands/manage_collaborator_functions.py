"""Abertura e encerramento de função operacional do colaborador (ADR-0013).

Função aqui é o que a pessoa **é** no negócio — consultor, BKO, finalização —,
distinta do perfil de acesso em `roles`, que é o que ela **pode fazer** no
sistema. Uma pessoa acumula funções: cada uma é uma linha própria em
`collaborator_roles`, com vigência.

Trocar de função **não é UPDATE**. Encerra-se a linha atual com `valid_to` e
abre-se outra com `valid_from`. Sobrescrever destruiria a resposta de "que
função essa pessoa tinha **na data daquela proposta**" — e é exatamente essa
pergunta que a regra de comissão faz. Uma proposta de março passaria a ser
comissionada pela função de outubro, e o histórico contaria uma mentira.

A mesma função não pode se sobrepor a si mesma; funções diferentes convivem, que
é o que "acumular função" significa.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.organization.domain.errors import (
    ColaboradorInativoError,
    RecursoNaoEncontradoError,
    VigenciaSobrepostaError,
)
from app.modules.organization.domain.policies.vigencia_policy import garantir_sem_sobreposicao
from app.modules.organization.domain.value_objects.papel_de_colaborador import (
    PapelDeColaborador,
)
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork
from app.shared.domain.date_range import DateRange

MODULO = "organization"


@dataclass(frozen=True, slots=True)
class AddCollaboratorFunction:
    collaborator_id: int
    funcao: PapelDeColaborador
    valid_from: date
    #: normalmente nulo — função nasce sem fim previsto
    valid_to: date | None = None
    ator: int | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class CloseCollaboratorFunction:
    collaborator_id: int
    function_id: int
    valid_to: date
    ator: int | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class FuncaoDoColaborador:
    id: int
    role: str
    valid_from: date
    valid_to: date | None


class AddCollaboratorFunctionHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        colaboradores: SqlCollaboratorRepository,
        audit: AuditRecorder,
    ) -> None:
        self._uow = uow
        self._colaboradores = colaboradores
        self._audit = audit

    async def execute(self, cmd: AddCollaboratorFunction) -> FuncaoDoColaborador:
        colaborador = await self._colaboradores.buscar_por_id(cmd.collaborator_id)
        if colaborador is None:
            raise RecursoNaoEncontradoError("Colaborador não encontrado.")
        if not colaborador.is_active:
            raise ColaboradorInativoError(
                "Colaborador inativo não recebe função nova. Reative o cadastro antes."
            )
        nova = _intervalo(cmd.valid_from, cmd.valid_to)

        # só a mesma função conflita: acumular consultor e líder é legítimo
        modalidades_consultor = {
            PapelDeColaborador.CONSULTOR,
            PapelDeColaborador.CONSULTOR_MEI_ESCALONADO,
        }
        if cmd.funcao in modalidades_consultor:
            mesmas = [
                papel
                for papel in await self._colaboradores.papeis_do_colaborador(cmd.collaborator_id)
                if PapelDeColaborador(papel.role) in modalidades_consultor
            ]
        else:
            mesmas = await self._colaboradores.papeis_do_colaborador(
                cmd.collaborator_id, papel=cmd.funcao.value
            )
        garantir_sem_sobreposicao(
            nova,
            [_intervalo(m.valid_from, m.valid_to) for m in mesmas],
            descricao=f"A função {cmd.funcao.value} a partir de {cmd.valid_from.isoformat()}",
        )

        modelo = await self._colaboradores.adicionar_papel(
            collaborator_id=cmd.collaborator_id,
            papel=cmd.funcao.value,
            valid_from=cmd.valid_from,
            valid_to=cmd.valid_to,
            ator=cmd.ator,
        )

        self._audit.registrar(
            module=MODULO,
            action="collaborator.function_opened",
            actor_user_id=cmd.ator,
            aggregate_type="collaborator",
            aggregate_id=str(cmd.collaborator_id),
            correlation_id=cmd.correlation_id,
            payload={
                "function_id": modelo.id,
                "role": cmd.funcao.value,
                "valid_from": cmd.valid_from.isoformat(),
                "valid_to": cmd.valid_to.isoformat() if cmd.valid_to else None,
            },
        )
        await self._uow.commit()

        return FuncaoDoColaborador(
            id=modelo.id,
            role=modelo.role,
            valid_from=modelo.valid_from,
            valid_to=modelo.valid_to,
        )


class CloseCollaboratorFunctionHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        colaboradores: SqlCollaboratorRepository,
        audit: AuditRecorder,
    ) -> None:
        self._uow = uow
        self._colaboradores = colaboradores
        self._audit = audit

    async def execute(self, cmd: CloseCollaboratorFunction) -> FuncaoDoColaborador:
        if await self._colaboradores.buscar_por_id(cmd.collaborator_id) is None:
            raise RecursoNaoEncontradoError("Colaborador não encontrado.")

        alvo = next(
            (
                p
                for p in await self._colaboradores.papeis_do_colaborador(cmd.collaborator_id)
                if p.id == cmd.function_id
            ),
            None,
        )
        if alvo is None:
            raise RecursoNaoEncontradoError("Função não encontrada neste colaborador.")
        if alvo.valid_to is not None:
            raise VigenciaSobrepostaError(
                f"A função já foi encerrada em {alvo.valid_to.isoformat()}."
            )
        if cmd.valid_to < alvo.valid_from:
            raise VigenciaSobrepostaError(
                "O encerramento não pode ser anterior ao início da função "
                f"({alvo.valid_from.isoformat()})."
            )

        await self._colaboradores.encerrar_papel(function_id=cmd.function_id, valid_to=cmd.valid_to)

        self._audit.registrar(
            module=MODULO,
            action="collaborator.function_closed",
            actor_user_id=cmd.ator,
            aggregate_type="collaborator",
            aggregate_id=str(cmd.collaborator_id),
            correlation_id=cmd.correlation_id,
            payload={
                "function_id": cmd.function_id,
                "role": alvo.role,
                "valid_to": cmd.valid_to.isoformat(),
            },
        )
        await self._uow.commit()

        return FuncaoDoColaborador(
            id=alvo.id, role=alvo.role, valid_from=alvo.valid_from, valid_to=cmd.valid_to
        )


def _intervalo(inicio: date, fim: date | None) -> DateRange:
    try:
        return DateRange(inicio, fim)
    except ValueError as exc:
        raise VigenciaSobrepostaError(str(exc)) from exc
