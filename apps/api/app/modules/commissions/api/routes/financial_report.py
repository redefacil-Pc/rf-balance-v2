from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.modules.commissions.api.schemas.financial_report import (
    FinancialReportBeneficiaryResponse,
    FinancialReportDetailPageResponse,
    FinancialReportDetailResponse,
    FinancialReportDetailSummaryResponse,
    FinancialReportResponse,
    FinancialReportSummaryResponse,
)
from app.modules.commissions.application.queries.financial_report import (
    FinancialCommissionReportQuery,
    FinancialReportBeneficiary,
    FinancialReportSummary,
)
from app.modules.identity.api.dependencies import Uow, require_permission
from app.modules.identity.domain.entities.user import User
from app.modules.reporting.application.financial_report_documents import (
    financial_report_pdf,
    financial_report_xlsx,
)

router = APIRouter(prefix="/api/v1", tags=["commission-reports"])


async def _report_data(
    uow: Uow,
    period_start: date,
    period_end: date,
    unit_id: int | None = None,
    leader_id: int | None = None,
) -> tuple[FinancialReportSummary, list[FinancialReportBeneficiary]]:
    return await FinancialCommissionReportQuery(uow.session).summary(
        period_start=period_start,
        period_end=period_end,
        unit_id=unit_id,
        leader_id=leader_id,
    )


@router.get("/commission-financial-report/export.xlsx")
async def export_financial_report_xlsx(
    period_start: Annotated[date, Query()],
    period_end: Annotated[date, Query()],
    uow: Uow,
    _exporter: Annotated[User, Depends(require_permission("reports:export"))],
    _financial_reader: Annotated[User, Depends(require_permission("settlements:read"))],
    unit_id: Annotated[int | None, Query(gt=0)] = None,
    leader_id: Annotated[int | None, Query(gt=0)] = None,
) -> Response:
    summary, beneficiaries = await _report_data(
        uow, period_start, period_end, unit_id, leader_id
    )
    return Response(
        financial_report_xlsx(summary, beneficiaries),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="relatorio-comissoes.xlsx"'},
    )


@router.get("/commission-financial-report/export.pdf")
async def export_financial_report_pdf(
    period_start: Annotated[date, Query()],
    period_end: Annotated[date, Query()],
    uow: Uow,
    _exporter: Annotated[User, Depends(require_permission("reports:export"))],
    _financial_reader: Annotated[User, Depends(require_permission("settlements:read"))],
    unit_id: Annotated[int | None, Query(gt=0)] = None,
    leader_id: Annotated[int | None, Query(gt=0)] = None,
) -> Response:
    summary, beneficiaries = await _report_data(
        uow, period_start, period_end, unit_id, leader_id
    )
    return Response(
        financial_report_pdf(summary, beneficiaries),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="relatorio-comissoes.pdf"'},
    )


@router.get("/commission-financial-report", response_model=FinancialReportResponse)
async def financial_report(
    period_start: Annotated[date, Query()],
    period_end: Annotated[date, Query()],
    uow: Uow,
    _actor: Annotated[User, Depends(require_permission("settlements:read"))],
    unit_id: Annotated[int | None, Query(gt=0)] = None,
    leader_id: Annotated[int | None, Query(gt=0)] = None,
) -> FinancialReportResponse:
    summary, beneficiaries = await FinancialCommissionReportQuery(uow.session).summary(
        period_start=period_start,
        period_end=period_end,
        unit_id=unit_id,
        leader_id=leader_id,
    )
    return FinancialReportResponse(
        period_start=period_start,
        period_end=period_end,
        summary=FinancialReportSummaryResponse(
            **{field: str(getattr(summary, field)) for field in summary.__dataclass_fields__}
        ),
        beneficiaries=[
            FinancialReportBeneficiaryResponse(
                beneficiary_id=item.beneficiary_id,
                beneficiary_name=item.beneficiary_name,
                strategies=list(item.strategies),
                automatic_amount=str(item.automatic_amount),
                manual_amount=str(item.manual_amount),
                calculated_amount=str(item.calculated_amount),
                carryover_amount=str(item.carryover_amount),
                bonus_amount=str(item.bonus_amount),
                discount_amount=str(item.discount_amount),
                deferred_amount=str(item.deferred_amount),
                paid_amount=str(item.paid_amount),
                payable_amount=str(item.payable_amount),
                status=item.status,
            )
            for item in beneficiaries
        ],
    )


@router.get(
    "/commission-financial-report/beneficiaries/{beneficiary_id}",
    response_model=FinancialReportDetailPageResponse,
)
async def financial_report_details(
    beneficiary_id: int,
    period_start: Annotated[date, Query()],
    period_end: Annotated[date, Query()],
    uow: Uow,
    _actor: Annotated[User, Depends(require_permission("settlements:read"))],
    unit_id: Annotated[int | None, Query(gt=0)] = None,
    leader_id: Annotated[int | None, Query(gt=0)] = None,
) -> FinancialReportDetailPageResponse:
    summary, items = await FinancialCommissionReportQuery(uow.session).details(
        beneficiary_id=beneficiary_id,
        period_start=period_start,
        period_end=period_end,
        unit_id=unit_id,
        leader_id=leader_id,
    )
    return FinancialReportDetailPageResponse(
        summary=FinancialReportDetailSummaryResponse(
            recognized_production=str(summary.recognized_production),
            received_amount=str(summary.received_amount),
            commission_amount=str(summary.commission_amount),
            deferred_amount=str(summary.deferred_amount),
        ),
        items=[
            FinancialReportDetailResponse(
                source=item.source,
                strategy=item.strategy,
                entry_type=item.entry_type,
                competence_date=item.competence_date,
                amount=str(item.amount),
                description=item.description,
                proposal_id=item.proposal_id,
                proposal_external_id=item.proposal_external_id,
                customer_name=item.customer_name,
                receipt_id=item.receipt_id,
                recognized_production=str(item.recognized_production),
                received_amount=str(item.received_amount),
                received_percentage=(
                    str(item.received_percentage) if item.received_percentage is not None else None
                ),
                tps_percentage=(
                    str(item.tps_percentage) if item.tps_percentage is not None else None
                ),
            )
            for item in items
        ],
    )
