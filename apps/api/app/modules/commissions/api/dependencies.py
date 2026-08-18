from fastapi import Request

from app.modules.audit.infrastructure.repositories.sql_audit_recorder import SqlAuditRecorder
from app.modules.commissions.application.manage_beneficiary_policies import (
    CommissionBeneficiaryPolicyManager,
)
from app.modules.commissions.application.manage_periods import CommissionPeriodManager
from app.modules.commissions.application.manage_rule_sets import CommissionRuleSetManager
from app.modules.commissions.application.manage_settlements import CommissionSettlementManager
from app.modules.commissions.application.manage_strategy_configs import (
    CommissionStrategyConfigManager,
)
from app.modules.identity.api.dependencies import Uow
from app.platform.bus.outbox_recorder import SqlOutboxRecorder


def get_rule_set_manager(request: Request, uow: Uow) -> CommissionRuleSetManager:
    return CommissionRuleSetManager(
        uow=uow,
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        outbox=SqlOutboxRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


def get_strategy_config_manager(request: Request, uow: Uow) -> CommissionStrategyConfigManager:
    return CommissionStrategyConfigManager(
        uow=uow,
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        outbox=SqlOutboxRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


def get_settlement_manager(request: Request, uow: Uow) -> CommissionSettlementManager:
    return CommissionSettlementManager(
        uow=uow,
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        outbox=SqlOutboxRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


def get_beneficiary_policy_manager(
    request: Request, uow: Uow
) -> CommissionBeneficiaryPolicyManager:
    return CommissionBeneficiaryPolicyManager(
        uow=uow,
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


def get_period_manager(request: Request, uow: Uow) -> CommissionPeriodManager:
    return CommissionPeriodManager(
        uow=uow,
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        outbox=SqlOutboxRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )
