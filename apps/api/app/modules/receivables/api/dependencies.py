from __future__ import annotations

from fastapi import Request

from app.modules.audit.infrastructure.repositories.sql_audit_recorder import SqlAuditRecorder
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    SqlProposalRepository,
)
from app.modules.commercial.infrastructure.storage.object_attachment_storage import (
    ObjectAttachmentStorage,
)
from app.modules.identity.api.dependencies import Uow
from app.modules.receivables.application.receipt_service import ReceiptService


def get_receipt_service(request: Request, uow: Uow) -> ReceiptService:
    return ReceiptService(
        uow=uow,
        proposals=SqlProposalRepository(uow.session, request.app.state.pii_cipher),
        storage=ObjectAttachmentStorage(
            request.app.state.storage,
            request.app.state.settings.storage.object_storage_bucket,
        ),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )
