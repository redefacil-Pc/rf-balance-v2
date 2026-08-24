from __future__ import annotations

from fastapi import Request

from app.modules.audit.infrastructure.repositories.sql_audit_recorder import SqlAuditRecorder
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    SqlProposalRepository,
)
from app.modules.commercial.infrastructure.storage.object_attachment_storage import (
    ObjectAttachmentStorage,
)
from app.modules.commissions.application.standard_commission_engine import (
    StandardCommissionEngine,
)
from app.modules.identity.api.dependencies import Uow
from app.modules.organization.infrastructure.repositories.sql_receiving_account_directory import (
    SqlReceivingAccountDirectory,
)
from app.modules.receivables.application.receipt_service import ReceiptService
from app.platform.bus.outbox_recorder import SqlOutboxRecorder


def get_receipt_service(request: Request, uow: Uow) -> ReceiptService:
    outbox = SqlOutboxRecorder(uow.session, request.app.state.clock)
    return ReceiptService(
        uow=uow,
        proposals=SqlProposalRepository(uow.session, request.app.state.pii_cipher),
        storage=ObjectAttachmentStorage(
            request.app.state.storage,
            request.app.state.settings.storage.object_storage_bucket,
            request.app.state.settings.storage.object_storage_prefix,
        ),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        outbox=outbox,
        commissions=StandardCommissionEngine(uow.session, outbox),
        contas=SqlReceivingAccountDirectory(uow.session),
        clock=request.app.state.clock,
        timezone=request.app.state.settings.app.app_timezone,
    )
