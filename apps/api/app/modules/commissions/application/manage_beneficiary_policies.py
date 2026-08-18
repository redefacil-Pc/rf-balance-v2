from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import or_, select

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.commissions.domain.errors import CommissionRuleConfigurationError
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionBeneficiaryPolicyModel,
)
from app.modules.organization.infrastructure.models.collaborator_model import CollaboratorModel
from app.modules.organization.infrastructure.models.collaborator_role_model import (
    CollaboratorRoleModel,
)
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import Clock


class CommissionBeneficiaryPolicyManager:
    def __init__(self, *, uow: UnitOfWork, audit: AuditRecorder, clock: Clock) -> None:
        self._uow = uow
        self._session = uow.session
        self._audit = audit
        self._clock = clock

    async def list(self) -> list[tuple[CommissionBeneficiaryPolicyModel, str]]:
        rows = (
            await self._session.execute(
                select(CommissionBeneficiaryPolicyModel, CollaboratorModel.full_name)
                .join(
                    CollaboratorModel,
                    CollaboratorModel.id == CommissionBeneficiaryPolicyModel.collaborator_id,
                )
                .order_by(
                    CommissionBeneficiaryPolicyModel.valid_from.desc(),
                    CollaboratorModel.full_name,
                )
            )
        ).all()
        return [(row[0], str(row[1])) for row in rows]

    async def create(
        self,
        *,
        collaborator_id: int,
        valid_from: date,
        excluded: bool,
        override: Decimal | None,
        reason: str,
        actor: int,
        correlation_id: str | None,
    ) -> CommissionBeneficiaryPolicyModel:
        collaborator = await self._session.get(CollaboratorModel, collaborator_id)
        if collaborator is None:
            raise CommissionRuleConfigurationError("Selecione um consultor válido.")
        consultant_role = await self._session.scalar(
            select(CollaboratorRoleModel.id).where(
                CollaboratorRoleModel.collaborator_id == collaborator_id,
                CollaboratorRoleModel.role.in_(("CONSULTOR", "CONSULTOR_MEI_ESCALONADO")),
                CollaboratorRoleModel.valid_from <= valid_from,
                or_(
                    CollaboratorRoleModel.valid_to.is_(None),
                    CollaboratorRoleModel.valid_to >= valid_from,
                ),
            )
        )
        if consultant_role is None:
            raise CommissionRuleConfigurationError(
                "A pessoa precisa ter função de consultor vigente nessa data."
            )
        if valid_from < self._clock.business_date():
            raise CommissionRuleConfigurationError(
                "A exceção individual não pode iniciar retroativamente."
            )
        if override is not None and not Decimal("0") <= override <= Decimal("100"):
            raise CommissionRuleConfigurationError("O override deve estar entre 0 e 100%.")
        if excluded and override is not None:
            raise CommissionRuleConfigurationError(
                "Uma exclusão total não pode ter percentual de override."
            )
        overlaps = list(
            (
                await self._session.scalars(
                    select(CommissionBeneficiaryPolicyModel)
                    .where(
                        CommissionBeneficiaryPolicyModel.collaborator_id == collaborator_id,
                        CommissionBeneficiaryPolicyModel.valid_from <= valid_from,
                        or_(
                            CommissionBeneficiaryPolicyModel.valid_to.is_(None),
                            CommissionBeneficiaryPolicyModel.valid_to >= valid_from,
                        ),
                    )
                    .with_for_update()
                )
            ).all()
        )
        for item in overlaps:
            item.valid_to = valid_from - timedelta(days=1)
        policy = CommissionBeneficiaryPolicyModel(
            collaborator_id=collaborator_id,
            valid_from=valid_from,
            excluded=excluded,
            override_tps_35_percentage=override,
            reason=reason.strip(),
            created_by=actor,
        )
        self._session.add(policy)
        await self._session.flush()
        self._audit.registrar(
            module="commissions",
            action="commission.beneficiary_policy_created",
            actor_user_id=actor,
            aggregate_type="commission_beneficiary_policy",
            aggregate_id=str(policy.id),
            correlation_id=correlation_id,
            payload={
                "collaborator_id": collaborator_id,
                "valid_from": valid_from.isoformat(),
                "excluded": excluded,
                "override_tps_35_percentage": None if override is None else str(override),
            },
        )
        await self._uow.commit()
        return policy
