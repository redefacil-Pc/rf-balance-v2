"""Manutenção auditável de empresas e unidades."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.organization.domain.errors import RecursoNaoEncontradoError
from app.modules.organization.infrastructure.repositories.sql_company_repository import (
    SqlCompanyRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class UpdateCompany:
    company_id: int
    legal_name: str
    trade_name: str
    ator: int | None
    correlation_id: str | None


@dataclass(frozen=True, slots=True)
class SetCompanyStatus:
    company_id: int
    ativo: bool
    ator: int | None
    correlation_id: str | None


@dataclass(frozen=True, slots=True)
class UpdateUnit:
    unit_id: int
    code: str
    name: str
    ator: int | None
    correlation_id: str | None


@dataclass(frozen=True, slots=True)
class SetUnitStatus:
    unit_id: int
    ativo: bool
    ator: int | None
    correlation_id: str | None


class CatalogHandler:
    def __init__(
        self, *, uow: UnitOfWork, empresas: SqlCompanyRepository, audit: AuditRecorder
    ) -> None:
        self._uow = uow
        self._empresas = empresas
        self._audit = audit

    async def update_company(self, cmd: UpdateCompany) -> None:
        model = await self._empresas.buscar_por_id(cmd.company_id)
        if model is None:
            raise RecursoNaoEncontradoError("Empresa não encontrada.")
        before = {"legal_name": model.legal_name, "trade_name": model.trade_name}
        await self._empresas.atualizar_empresa(
            company_id=cmd.company_id,
            legal_name=cmd.legal_name.strip(),
            trade_name=cmd.trade_name.strip(),
            ator=cmd.ator,
        )
        self._audit.registrar(
            module="organization",
            action="company.updated",
            actor_user_id=cmd.ator,
            aggregate_type="company",
            aggregate_id=str(cmd.company_id),
            correlation_id=cmd.correlation_id,
            payload={
                "antes": before,
                "depois": {
                    "legal_name": cmd.legal_name.strip(),
                    "trade_name": cmd.trade_name.strip(),
                },
            },
        )
        await self._uow.commit()

    async def set_company_status(self, cmd: SetCompanyStatus) -> None:
        model = await self._empresas.buscar_por_id(cmd.company_id)
        if model is None:
            raise RecursoNaoEncontradoError("Empresa não encontrada.")
        await self._empresas.definir_situacao_empresa(
            company_id=cmd.company_id, ativo=cmd.ativo, ator=cmd.ator
        )
        self._audit.registrar(
            module="organization",
            action="company.activated" if cmd.ativo else "company.deactivated",
            actor_user_id=cmd.ator,
            aggregate_type="company",
            aggregate_id=str(cmd.company_id),
            correlation_id=cmd.correlation_id,
            payload={"legal_name": model.legal_name},
        )
        await self._uow.commit()

    async def update_unit(self, cmd: UpdateUnit) -> None:
        model = await self._empresas.buscar_unidade(cmd.unit_id)
        if model is None:
            raise RecursoNaoEncontradoError("Unidade não encontrada.")
        before = {"code": model.code, "name": model.name}
        await self._empresas.atualizar_unidade(
            unit_id=cmd.unit_id, code=cmd.code.strip().upper(), name=cmd.name.strip(), ator=cmd.ator
        )
        self._audit.registrar(
            module="organization",
            action="unit.updated",
            actor_user_id=cmd.ator,
            aggregate_type="unit",
            aggregate_id=str(cmd.unit_id),
            correlation_id=cmd.correlation_id,
            payload={
                "antes": before,
                "depois": {"code": cmd.code.strip().upper(), "name": cmd.name.strip()},
            },
        )
        await self._uow.commit()

    async def set_unit_status(self, cmd: SetUnitStatus) -> None:
        model = await self._empresas.buscar_unidade(cmd.unit_id)
        if model is None:
            raise RecursoNaoEncontradoError("Unidade não encontrada.")
        await self._empresas.definir_situacao_unidade(
            unit_id=cmd.unit_id, ativo=cmd.ativo, ator=cmd.ator
        )
        self._audit.registrar(
            module="organization",
            action="unit.activated" if cmd.ativo else "unit.deactivated",
            actor_user_id=cmd.ator,
            aggregate_type="unit",
            aggregate_id=str(cmd.unit_id),
            correlation_id=cmd.correlation_id,
            payload={"code": model.code},
        )
        await self._uow.commit()
