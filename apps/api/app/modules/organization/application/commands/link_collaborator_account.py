"""Caso de uso: ligar (ou desligar) a conta de acesso de um colaborador.

A coluna `collaborators.user_id` existia desde o início e nunca era escrita —
declarada e sempre nula. É ela que responde "quais resultados são desta pessoa",
e sem preenchê-la um consultor logado não é identificável como consultor nenhum:
a única leitura possível seria a base inteira.

Mora em `organization` porque a coluna é da tabela de colaboradores. `identity`
apenas lê, através de porta.

O vínculo é 1:1 nos dois sentidos — uma conta para um colaborador. Duas contas
para a mesma pessoa dividiriam o histórico dela; uma conta em dois colaboradores
tornaria "meus resultados" ambíguo.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.organization.domain.errors import (
    ContaInativaError,
    ContaJaVinculadaError,
    RecursoNaoEncontradoError,
)
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork

MODULO = "organization"


@dataclass(frozen=True, slots=True)
class LinkCollaboratorAccount:
    collaborator_id: int
    #: `None` desfaz o vínculo
    user_id: int | None
    ator: int | None = None
    correlation_id: str | None = None


class LinkCollaboratorAccountHandler:
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

    async def execute(self, cmd: LinkCollaboratorAccount) -> None:
        colaborador = await self._colaboradores.buscar_por_id(cmd.collaborator_id)
        if colaborador is None:
            raise RecursoNaoEncontradoError("Colaborador não encontrado.")

        anterior = colaborador.user_id

        if cmd.user_id is not None:
            situacao = await self._colaboradores.situacao_da_conta(cmd.user_id)
            if situacao is None:
                raise RecursoNaoEncontradoError("Conta de acesso não encontrada.")
            if not situacao:
                raise ContaInativaError("Reative a conta antes de vinculá-la ao colaborador.")
            dono = await self._colaboradores.colaborador_da_conta(cmd.user_id)
            if dono is not None and dono.id != cmd.collaborator_id:
                raise ContaJaVinculadaError(f"A conta já pertence ao colaborador {dono.full_name}.")

        await self._colaboradores.definir_conta(
            collaborator_id=cmd.collaborator_id, user_id=cmd.user_id
        )

        self._audit.registrar(
            module=MODULO,
            action="collaborator.account_linked"
            if cmd.user_id is not None
            else "collaborator.account_unlinked",
            actor_user_id=cmd.ator,
            aggregate_type="collaborator",
            aggregate_id=str(cmd.collaborator_id),
            correlation_id=cmd.correlation_id,
            payload={"antes": anterior, "depois": cmd.user_id},
        )
        await self._uow.commit()
