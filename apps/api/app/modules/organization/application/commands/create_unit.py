"""Caso de uso: cadastrar unidade de uma empresa."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.organization.domain.errors import RecursoNaoEncontradoError
from app.modules.organization.infrastructure.repositories.sql_company_repository import (
    SqlCompanyRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork

MODULO = "organization"


@dataclass(frozen=True, slots=True)
class CreateUnit:
    company_id: int
    code: str
    name: str
    ator: int | None
    correlation_id: str | None


@dataclass(frozen=True, slots=True)
class UnidadeCriada:
    id: int
    code: str
    name: str
    company_id: int


class CreateUnitHandler:
    def __init__(
        self, *, uow: UnitOfWork, empresas: SqlCompanyRepository, audit: AuditRecorder
    ) -> None:
        self._uow = uow
        self._empresas = empresas
        self._audit = audit

    async def execute(self, cmd: CreateUnit) -> UnidadeCriada:
        empresa = await self._empresas.buscar_por_id(cmd.company_id)
        if empresa is None:
            raise RecursoNaoEncontradoError("Empresa não encontrada.")

        unidade = await self._empresas.criar_unidade(
            company_id=cmd.company_id,
            code=cmd.code.strip().upper(),
            name=cmd.name.strip(),
            ator=cmd.ator,
        )
        self._audit.registrar(
            module=MODULO,
            action="unit.created",
            actor_user_id=cmd.ator,
            aggregate_type="unit",
            aggregate_id=str(unidade.id),
            correlation_id=cmd.correlation_id,
            payload={"company_id": cmd.company_id, "code": unidade.code},
        )
        await self._uow.commit()

        return UnidadeCriada(
            id=unidade.id, code=unidade.code, name=unidade.name, company_id=unidade.company_id
        )
