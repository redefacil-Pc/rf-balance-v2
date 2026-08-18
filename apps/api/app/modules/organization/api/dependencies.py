"""Montagem dos handlers do módulo de organização."""

from __future__ import annotations

from fastapi import Request

from app.modules.audit.infrastructure.repositories.sql_audit_recorder import SqlAuditRecorder
from app.modules.identity.api.dependencies import Uow
from app.modules.organization.application.commands.create_collaborator import (
    CreateCollaboratorHandler,
)
from app.modules.organization.application.commands.create_company import CreateCompanyHandler
from app.modules.organization.application.commands.create_unit import CreateUnitHandler
from app.modules.organization.application.commands.deactivate_collaborator import (
    ActivateCollaboratorHandler,
    DeactivateCollaboratorHandler,
)
from app.modules.organization.application.commands.link_collaborator_account import (
    LinkCollaboratorAccountHandler,
)
from app.modules.organization.application.commands.manage_bank_account import BankAccountHandler
from app.modules.organization.application.commands.manage_catalog import CatalogHandler
from app.modules.organization.application.commands.manage_collaborator_functions import (
    AddCollaboratorFunctionHandler,
    CloseCollaboratorFunctionHandler,
)
from app.modules.organization.application.commands.update_collaborator import (
    UpdateCollaboratorHandler,
)
from app.modules.organization.application.queries.list_collaborator_functions import (
    ListCollaboratorFunctionsHandler,
)
from app.modules.organization.application.queries.list_collaborators import (
    ListCollaboratorsHandler,
)
from app.modules.organization.infrastructure.repositories.sql_bank_account_repository import (
    SqlBankAccountRepository,
)
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.modules.organization.infrastructure.repositories.sql_company_repository import (
    SqlCompanyRepository,
)
from app.modules.teams.infrastructure.repositories.sql_team_assignment_repository import (
    SqlTeamAssignmentRepository,
)


def get_create_company_handler(request: Request, uow: Uow) -> CreateCompanyHandler:
    return CreateCompanyHandler(
        uow=uow,
        empresas=SqlCompanyRepository(uow.session),
        cipher=request.app.state.pii_cipher,
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
    )


def get_create_unit_handler(request: Request, uow: Uow) -> CreateUnitHandler:
    return CreateUnitHandler(
        uow=uow,
        empresas=SqlCompanyRepository(uow.session),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
    )


def get_create_collaborator_handler(request: Request, uow: Uow) -> CreateCollaboratorHandler:
    return CreateCollaboratorHandler(
        uow=uow,
        colaboradores=SqlCollaboratorRepository(uow.session),
        empresas=SqlCompanyRepository(uow.session),
        cipher=request.app.state.pii_cipher,
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


def get_deactivate_collaborator_handler(
    request: Request, uow: Uow
) -> DeactivateCollaboratorHandler:
    return DeactivateCollaboratorHandler(
        uow=uow,
        colaboradores=SqlCollaboratorRepository(uow.session),
        vinculos=SqlTeamAssignmentRepository(uow.session),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


def get_activate_collaborator_handler(request: Request, uow: Uow) -> ActivateCollaboratorHandler:
    return ActivateCollaboratorHandler(
        uow=uow,
        colaboradores=SqlCollaboratorRepository(uow.session),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


def get_update_collaborator_handler(request: Request, uow: Uow) -> UpdateCollaboratorHandler:
    return UpdateCollaboratorHandler(
        uow=uow,
        colaboradores=SqlCollaboratorRepository(uow.session),
        empresas=SqlCompanyRepository(uow.session),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        cipher=request.app.state.pii_cipher,
        clock=request.app.state.clock,
    )


def get_list_collaborators_handler(request: Request, uow: Uow) -> ListCollaboratorsHandler:
    return ListCollaboratorsHandler(
        colaboradores=SqlCollaboratorRepository(uow.session),
        cipher=request.app.state.pii_cipher,
    )


def get_link_account_handler(request: Request, uow: Uow) -> LinkCollaboratorAccountHandler:
    return LinkCollaboratorAccountHandler(
        uow=uow,
        colaboradores=SqlCollaboratorRepository(uow.session),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
    )


def get_add_function_handler(request: Request, uow: Uow) -> AddCollaboratorFunctionHandler:
    return AddCollaboratorFunctionHandler(
        uow=uow,
        colaboradores=SqlCollaboratorRepository(uow.session),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
    )


def get_close_function_handler(request: Request, uow: Uow) -> CloseCollaboratorFunctionHandler:
    return CloseCollaboratorFunctionHandler(
        uow=uow,
        colaboradores=SqlCollaboratorRepository(uow.session),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
    )


def get_list_functions_handler(uow: Uow) -> ListCollaboratorFunctionsHandler:
    return ListCollaboratorFunctionsHandler(colaboradores=SqlCollaboratorRepository(uow.session))


def get_company_repository(uow: Uow) -> SqlCompanyRepository:
    return SqlCompanyRepository(uow.session)


def get_catalog_handler(request: Request, uow: Uow) -> CatalogHandler:
    return CatalogHandler(
        uow=uow,
        empresas=SqlCompanyRepository(uow.session),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
    )


def get_bank_account_handler(request: Request, uow: Uow) -> BankAccountHandler:
    return BankAccountHandler(
        uow=uow,
        accounts=SqlBankAccountRepository(uow.session),
        collaborators=SqlCollaboratorRepository(uow.session),
        cipher=request.app.state.pii_cipher,
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
    )
