"""Registro de models para o Alembic.

O autogenerate e o `alembic check` só veem tabelas cujo model foi importado.
Model novo entra aqui, senão a migração nasce incompleta e o readiness passa a
divergir sem motivo aparente.
"""

from app.modules.audit.infrastructure.models.audit_event_model import AuditEventModel
from app.modules.commercial.infrastructure.models.proposal_attachment_model import (
    ProposalAttachmentModel,
)
from app.modules.commercial.infrastructure.models.proposal_model import ProposalModel
from app.modules.identity.infrastructure.models.login_attempt_model import LoginAttemptModel
from app.modules.identity.infrastructure.models.permission_model import PermissionModel
from app.modules.identity.infrastructure.models.role_model import RoleModel
from app.modules.identity.infrastructure.models.role_permission_model import RolePermissionModel
from app.modules.identity.infrastructure.models.session_model import SessionModel
from app.modules.identity.infrastructure.models.user_model import UserModel
from app.modules.identity.infrastructure.models.user_role_model import UserRoleModel
from app.modules.legacy.infrastructure.models.legacy_import_issue_model import (
    LegacyImportIssueModel,
)
from app.modules.legacy.infrastructure.models.legacy_import_run_model import LegacyImportRunModel
from app.modules.organization.infrastructure.models.bank_account_model import BankAccountModel
from app.modules.organization.infrastructure.models.collaborator_model import CollaboratorModel
from app.modules.organization.infrastructure.models.collaborator_payment_key_model import (
    CollaboratorPaymentKeyModel,
)
from app.modules.organization.infrastructure.models.collaborator_role_model import (
    CollaboratorRoleModel,
)
from app.modules.organization.infrastructure.models.company_model import CompanyModel
from app.modules.organization.infrastructure.models.unit_model import UnitModel
from app.modules.receivables.infrastructure.models.receipt_model import (
    ReceiptModel,
    ReceiptReversalModel,
)
from app.modules.teams.infrastructure.models.team_assignment_model import TeamAssignmentModel
from app.platform.bus.outbox_model import OutboxEventModel

__all__ = [
    "AuditEventModel",
    "BankAccountModel",
    "CollaboratorModel",
    "CollaboratorPaymentKeyModel",
    "CollaboratorRoleModel",
    "CompanyModel",
    "LegacyImportIssueModel",
    "LegacyImportRunModel",
    "LoginAttemptModel",
    "OutboxEventModel",
    "PermissionModel",
    "ProposalAttachmentModel",
    "ProposalModel",
    "ReceiptModel",
    "ReceiptReversalModel",
    "RoleModel",
    "RolePermissionModel",
    "SessionModel",
    "TeamAssignmentModel",
    "UnitModel",
    "UserModel",
    "UserRoleModel",
]
