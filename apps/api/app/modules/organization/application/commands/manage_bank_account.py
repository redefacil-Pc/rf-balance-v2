from __future__ import annotations

from dataclasses import dataclass

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.organization.domain.errors import (
    DadosBancariosInvalidosError,
    RecursoNaoEncontradoError,
)
from app.modules.organization.infrastructure.repositories.sql_bank_account_repository import (
    SqlBankAccountRepository,
)
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.security.pii_cipher import PiiCipher


@dataclass(frozen=True, slots=True)
class SaveBankAccount:
    collaborator_id: int
    account_id: int | None
    bank_code: str
    bank_name: str
    branch: str
    account_number: str | None
    account_type: str
    actor: int | None
    correlation_id: str | None


class BankAccountHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        accounts: SqlBankAccountRepository,
        collaborators: SqlCollaboratorRepository,
        cipher: PiiCipher,
        audit: AuditRecorder,
    ) -> None:
        self._uow = uow
        self._accounts = accounts
        self._collaborators = collaborators
        self._cipher = cipher
        self._audit = audit

    async def save(self, cmd: SaveBankAccount) -> int:
        collaborator = await self._collaborators.buscar_por_id(cmd.collaborator_id)
        if collaborator is None:
            raise RecursoNaoEncontradoError("Colaborador não encontrado.")
        encrypted = self._cipher.cifrar(cmd.account_number.strip()) if cmd.account_number else None
        masked = _mask(cmd.account_number.strip()) if cmd.account_number else None
        if cmd.account_id is None:
            if encrypted is None or masked is None:
                raise DadosBancariosInvalidosError("Número da conta é obrigatório.")
            model = await self._accounts.create(
                collaborator_id=cmd.collaborator_id,
                company_id=collaborator.company_id,
                bank_code=cmd.bank_code.strip(),
                bank_name=cmd.bank_name.strip(),
                branch=cmd.branch.strip(),
                account_encrypted=encrypted,
                account_masked=masked,
                account_type=cmd.account_type,
                actor=cmd.actor,
            )
            account_id = model.id
            action = "bank_account.created"
        else:
            if (
                await self._accounts.get_for_collaborator(cmd.account_id, cmd.collaborator_id)
                is None
            ):
                raise RecursoNaoEncontradoError("Conta bancária não encontrada.")
            await self._accounts.update(
                account_id=cmd.account_id,
                bank_code=cmd.bank_code.strip(),
                bank_name=cmd.bank_name.strip(),
                branch=cmd.branch.strip(),
                account_encrypted=encrypted,
                account_masked=masked,
                account_type=cmd.account_type,
                actor=cmd.actor,
            )
            account_id = cmd.account_id
            action = "bank_account.updated"
        self._audit.registrar(
            module="organization",
            action=action,
            actor_user_id=cmd.actor,
            aggregate_type="bank_account",
            aggregate_id=str(account_id),
            correlation_id=cmd.correlation_id,
            payload={
                "collaborator_id": cmd.collaborator_id,
                "bank_code": cmd.bank_code,
                "account_type": cmd.account_type,
            },
        )
        await self._uow.commit()
        return account_id

    async def set_status(
        self,
        *,
        collaborator_id: int,
        account_id: int,
        active: bool,
        actor: int | None,
        correlation_id: str | None,
    ) -> None:
        if await self._accounts.get_for_collaborator(account_id, collaborator_id) is None:
            raise RecursoNaoEncontradoError("Conta bancária não encontrada.")
        await self._accounts.set_status(account_id, active=active, actor=actor)
        self._audit.registrar(
            module="organization",
            action="bank_account.activated" if active else "bank_account.deactivated",
            actor_user_id=actor,
            aggregate_type="bank_account",
            aggregate_id=str(account_id),
            correlation_id=correlation_id,
            payload={"collaborator_id": collaborator_id},
        )
        await self._uow.commit()


def _mask(value: str) -> str:
    return f"****{value[-4:]}" if len(value) > 4 else "*" * len(value)
