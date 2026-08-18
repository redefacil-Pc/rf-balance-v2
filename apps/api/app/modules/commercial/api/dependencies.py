"""Montagem dos handlers do módulo comercial.

`OpenPeriodGate` é o ponto de troca da F5: quando `accounting_periods` existir, a
implementação de `periods` entra aqui e nenhum caso de uso muda.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.modules.audit.infrastructure.repositories.sql_audit_recorder import SqlAuditRecorder
from app.modules.commercial.application.commands.add_proposal_attachment import (
    AddProposalAttachmentHandler,
)
from app.modules.commercial.application.commands.cancel_proposal import CancelProposalHandler
from app.modules.commercial.application.commands.create_proposal import CreateProposalHandler
from app.modules.commercial.application.commands.decide_proposal import DecideProposalHandler
from app.modules.commercial.application.commands.remove_proposal_attachment import (
    RemoveProposalAttachmentHandler,
)
from app.modules.commercial.application.commands.submit_proposal import SubmitProposalHandler
from app.modules.commercial.application.commands.update_proposal import UpdateProposalHandler
from app.modules.commercial.application.ports.proposal_scope import EscopoDePropostas
from app.modules.commercial.application.queries.get_attachment_content import (
    GetAttachmentContentHandler,
)
from app.modules.commercial.application.queries.get_proposal import GetProposalHandler
from app.modules.commercial.application.queries.list_proposal_attachments import (
    ListProposalAttachmentsHandler,
)
from app.modules.commercial.application.queries.list_proposals import ListProposalsHandler
from app.modules.commercial.infrastructure.gates.open_period_gate import OpenPeriodGate
from app.modules.commercial.infrastructure.repositories.sql_proposal_attachment_repository import (
    SqlProposalAttachmentRepository,
)
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    SqlProposalRepository,
)
from app.modules.commercial.infrastructure.scope.rbac_proposal_scope import RbacProposalScope
from app.modules.commercial.infrastructure.storage.object_attachment_storage import (
    ObjectAttachmentStorage,
)
from app.modules.commissions.application.standard_commission_engine import (
    StandardCommissionEngine,
)
from app.modules.identity.api.dependencies import CurrentUser, Uow
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.modules.receivables.infrastructure.recognizers.sql_receipt_recognizer import (
    SqlReceiptRecognizer,
)
from app.modules.teams.infrastructure.repositories.sql_team_assignment_repository import (
    SqlTeamAssignmentRepository,
)
from app.platform.bus.outbox_recorder import SqlOutboxRecorder


async def get_proposal_scope(request: Request, uow: Uow, ator: CurrentUser) -> EscopoDePropostas:
    """Recorte de leitura do usuário logado, resolvido uma vez por request.

    Depende de `CurrentUser`, que o FastAPI já resolveu para o `require_permission`
    da rota — o cache de dependências evita repetir a consulta de sessão.
    """
    resolver = RbacProposalScope(
        SqlCollaboratorRepository(uow.session),
        SqlTeamAssignmentRepository(uow.session),
    )
    return await resolver.resolver(
        user_id=ator.id,
        papeis=frozenset(ator.roles),
        # a data de negócio decide qual equipe valia: quem lidera hoje pode não
        # ter liderado quando a proposta foi cadastrada
        referencia=request.app.state.clock.business_date(),
    )


Escopo = Annotated[EscopoDePropostas, Depends(get_proposal_scope)]


def _attachment_storage(request: Request) -> ObjectAttachmentStorage:
    return ObjectAttachmentStorage(
        request.app.state.storage,
        request.app.state.settings.storage.object_storage_bucket,
    )


def get_create_proposal_handler(request: Request, uow: Uow) -> CreateProposalHandler:
    return CreateProposalHandler(
        uow=uow,
        propostas=SqlProposalRepository(uow.session, request.app.state.pii_cipher),
        colaboradores=SqlCollaboratorRepository(uow.session),
        cipher=request.app.state.pii_cipher,
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
    )


def get_update_proposal_handler(request: Request, uow: Uow) -> UpdateProposalHandler:
    return UpdateProposalHandler(
        uow=uow,
        propostas=SqlProposalRepository(uow.session, request.app.state.pii_cipher),
        colaboradores=SqlCollaboratorRepository(uow.session),
        periodos=OpenPeriodGate(),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


def get_cancel_proposal_handler(request: Request, uow: Uow) -> CancelProposalHandler:
    return CancelProposalHandler(
        uow=uow,
        propostas=SqlProposalRepository(uow.session, request.app.state.pii_cipher),
        periodos=OpenPeriodGate(),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


def get_list_proposals_handler(request: Request, uow: Uow) -> ListProposalsHandler:
    return ListProposalsHandler(
        propostas=SqlProposalRepository(uow.session, request.app.state.pii_cipher),
        colaboradores=SqlCollaboratorRepository(uow.session),
        cipher=request.app.state.pii_cipher,
    )


def get_get_proposal_handler(request: Request, uow: Uow) -> GetProposalHandler:
    return GetProposalHandler(
        propostas=SqlProposalRepository(uow.session, request.app.state.pii_cipher),
        colaboradores=SqlCollaboratorRepository(uow.session),
        cipher=request.app.state.pii_cipher,
    )


def get_submit_proposal_handler(request: Request, uow: Uow) -> SubmitProposalHandler:
    return SubmitProposalHandler(
        uow=uow,
        propostas=SqlProposalRepository(uow.session, request.app.state.pii_cipher),
        anexos=SqlProposalAttachmentRepository(uow.session),
        recebimentos=SqlReceiptRecognizer(uow.session, request.app.state.clock.now()),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


def get_decide_proposal_handler(request: Request, uow: Uow) -> DecideProposalHandler:
    outbox = SqlOutboxRecorder(uow.session, request.app.state.clock)
    return DecideProposalHandler(
        uow=uow,
        propostas=SqlProposalRepository(uow.session, request.app.state.pii_cipher),
        # ponto de composição: `commercial` conhece a porta, não o `receivables`
        recebimentos=SqlReceiptRecognizer(uow.session, request.app.state.clock.now()),
        comissoes=StandardCommissionEngine(uow.session, outbox),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        outbox=outbox,
        clock=request.app.state.clock,
    )


def get_add_attachment_handler(request: Request, uow: Uow) -> AddProposalAttachmentHandler:
    return AddProposalAttachmentHandler(
        uow=uow,
        propostas=SqlProposalRepository(uow.session, request.app.state.pii_cipher),
        anexos=SqlProposalAttachmentRepository(uow.session),
        storage=_attachment_storage(request),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
    )


def get_remove_attachment_handler(request: Request, uow: Uow) -> RemoveProposalAttachmentHandler:
    return RemoveProposalAttachmentHandler(
        uow=uow,
        propostas=SqlProposalRepository(uow.session, request.app.state.pii_cipher),
        anexos=SqlProposalAttachmentRepository(uow.session),
        storage=_attachment_storage(request),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
    )


def get_list_attachments_handler(request: Request, uow: Uow) -> ListProposalAttachmentsHandler:
    return ListProposalAttachmentsHandler(
        propostas=SqlProposalRepository(uow.session, request.app.state.pii_cipher),
        anexos=SqlProposalAttachmentRepository(uow.session),
    )


def get_get_attachment_content_handler(request: Request, uow: Uow) -> GetAttachmentContentHandler:
    return GetAttachmentContentHandler(
        propostas=SqlProposalRepository(uow.session, request.app.state.pii_cipher),
        anexos=SqlProposalAttachmentRepository(uow.session),
        storage=_attachment_storage(request),
    )
