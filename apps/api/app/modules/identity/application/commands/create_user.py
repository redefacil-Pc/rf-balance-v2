"""Caso de uso: criar conta de acesso.

Quem cria não escolhe a senha de outra pessoa: o comando gera uma senha
provisória, devolve **uma única vez** para o operador repassar, e a conta nasce
com `must_change_password`. Assim ninguém além do dono termina conhecendo a
senha em uso — inclusive quem administra.

Papel é obrigatório: conta sem papel loga e não enxerga nada, e o erro só
aparece quando a pessoa tenta trabalhar.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.identity.application.ports.password_hasher import PasswordHasher
from app.modules.identity.domain.errors import (
    EmailInvalidoError,
    EmailJaCadastradoError,
    PapelInexistenteError,
    UsuarioSemPapelError,
)
from app.modules.identity.domain.value_objects.email_address import EmailAddress
from app.modules.identity.infrastructure.repositories.sql_user_repository import SqlUserRepository
from app.modules.organization.application.commands.create_collaborator import (
    CreateCollaborator,
    CreateCollaboratorHandler,
)
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork

MODULO = "identity"

#: comprimento da senha provisória; `token_urlsafe` rende ~1,3 caractere por byte
_BYTES_DA_SENHA = 12


@dataclass(frozen=True, slots=True)
class CreateUser:
    email: str
    full_name: str
    papeis: tuple[str, ...]
    colaborador: CreateCollaborator | None = None
    ator: int | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class UsuarioCriado:
    id: int
    email: str
    full_name: str
    papeis: tuple[str, ...]
    #: exibida uma única vez; não fica recuperável em lugar nenhum
    senha_provisoria: str
    colaborador_id: int | None = None


class CreateUserHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        users: SqlUserRepository,
        hasher: PasswordHasher,
        audit: AuditRecorder,
        collaborator_creator: CreateCollaboratorHandler,
        collaborators: SqlCollaboratorRepository,
    ) -> None:
        self._uow = uow
        self._users = users
        self._hasher = hasher
        self._audit = audit
        self._collaborator_creator = collaborator_creator
        self._collaborators = collaborators

    async def execute(self, cmd: CreateUser) -> UsuarioCriado:
        email = _normalizar(cmd.email)
        nome = cmd.full_name.strip()

        if await self._users.existe_email(email):
            raise EmailJaCadastradoError(email.valor)

        role_ids = await self._resolver_papeis(cmd.papeis)

        senha = secrets.token_urlsafe(_BYTES_DA_SENHA)
        modelo = await self._users.criar(
            email=email,
            full_name=nome,
            password_hash=self._hasher.gerar(senha),
            must_change_password=True,
        )
        await self._users.substituir_papeis(modelo.id, role_ids)

        colaborador_id = None
        if cmd.colaborador is not None:
            criado = await self._collaborator_creator.execute(cmd.colaborador, commit=False)
            colaborador_id = criado.id
            await self._collaborators.definir_conta(
                collaborator_id=criado.id, user_id=modelo.id
            )

        self._audit.registrar(
            module=MODULO,
            action="user.created",
            actor_user_id=cmd.ator,
            aggregate_type="user",
            aggregate_id=str(modelo.id),
            correlation_id=cmd.correlation_id,
            # e-mail identifica a conta e é o que se procura na trilha; senha e
            # hash jamais entram no payload
            payload={"email": email.valor, "roles": sorted(cmd.papeis)},
        )
        await self._uow.commit()

        return UsuarioCriado(
            id=modelo.id,
            email=email.valor,
            full_name=nome,
            papeis=tuple(sorted(cmd.papeis)),
            senha_provisoria=senha,
            colaborador_id=colaborador_id,
        )

    async def _resolver_papeis(self, codigos: tuple[str, ...]) -> list[int]:
        if not codigos:
            raise UsuarioSemPapelError()
        encontrados = await self._users.papeis_por_codigo(codigos)
        faltando = sorted(set(codigos) - set(encontrados))
        if faltando:
            raise PapelInexistenteError(f"Papel não encontrado: {', '.join(faltando)}.")
        return [encontrados[code].id for code in sorted(set(codigos))]


def _normalizar(bruto: str) -> EmailAddress:
    try:
        return EmailAddress.normalizar(bruto)
    except ValueError as exc:
        raise EmailInvalidoError(str(exc)) from exc
