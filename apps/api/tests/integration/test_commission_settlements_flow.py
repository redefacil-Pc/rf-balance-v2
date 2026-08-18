from typing import Any

import pytest
from httpx import AsyncClient

from app.platform.config.security import CSRF_COOKIE, CSRF_HEADER
from app.platform.config.settings import get_settings
from app.platform.time.clock import SystemClock

pytestmark = pytest.mark.integration


async def _login_admin(cliente: AsyncClient, admin_semeado: dict[str, str]) -> dict[str, str]:
    login = await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )
    assert login.status_code == 200
    return {CSRF_HEADER: cliente.cookies[CSRF_COOKIE]}


async def test_bko_fechamento_ajustes_adiamento_e_pagamento(
    cliente: AsyncClient, admin_semeado: dict[str, str]
) -> None:
    csrf = await _login_admin(cliente, admin_semeado)

    company = await cliente.post(
        "/api/v1/companies",
        json={"legal_name": "Empresa Fechamento", "trade_name": "Fechamento"},
        headers=csrf,
    )
    assert company.status_code == 201, company.text
    bko = await cliente.post(
        "/api/v1/collaborators",
        json={
            "company_id": company.json()["id"],
            "unit_id": None,
            "full_name": "BKO de Teste",
            "document": "168.995.350-09",
            "tax_regime": "MEI",
            "roles": [{"role": "BKO", "valid_from": "2026-01-01"}],
        },
        headers=csrf,
    )
    assert bko.status_code == 201, bko.text
    manual = await cliente.post(
        "/api/v1/commission-bko-entries",
        json={
            "beneficiary_id": bko.json()["id"],
            "amount": "100.00",
            "effective_date": "2026-08-07",
            "description": "Comissão semanal de BKO",
        },
        headers={**csrf, "Idempotency-Key": "bko-settlement-test"},
    )
    assert manual.status_code == 201, manual.text

    period: dict[str, Any] = {"period_start": "2026-08-07", "period_end": "2026-08-13"}
    generated = await cliente.post(
        "/api/v1/commission-settlements/generation", json=period, headers=csrf
    )
    assert generated.status_code == 200, generated.text
    settlement = generated.json()["items"][0]
    assert settlement["roles"] == ["BKO"]
    assert settlement["gross_amount"] == "100.00"
    assert settlement["payable_amount"] == "100.00"

    adjusted = await cliente.put(
        f"/api/v1/commission-settlements/{settlement['id']}/adjustments",
        json={
            "bonus_amount": "20.00",
            "discount_amount": "10.00",
            "deferred_amount": "30.00",
            "notes": "30 reais para a próxima semana",
        },
        headers=csrf,
    )
    assert adjusted.status_code == 200, adjusted.text
    assert adjusted.json()["payable_amount"] == "80.00"
    assert adjusted.json()["status"] == "DEFERRED"

    paid = await cliente.post(
        f"/api/v1/commission-settlements/{settlement['id']}/payments",
        json={
            "amount": "80.00",
            "payment_date": "2026-08-17",
            "payment_method": "PIX",
            "reference": "PIX-TESTE",
        },
        headers=csrf,
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["payable_amount"] == "0.00"
    assert paid.json()["status"] == "DEFERRED"

    report = await cliente.get(
        "/api/v1/commission-financial-report",
        params=period,
    )
    assert report.status_code == 200, report.text
    expected_summary = {
        "bko_commissions": "100.00",
        "total_commissions": "100.00",
        "net_billing": "-100.00",
        "paid": "80.00",
        "payable": "0.00",
    }
    assert all(report.json()["summary"][key] == value for key, value in expected_summary.items())
    beneficiary = next(
        item
        for item in report.json()["beneficiaries"]
        if item["beneficiary_id"] == bko.json()["id"]
    )
    assert beneficiary["manual_amount"] == "100.00"
    detail = await cliente.get(
        f"/api/v1/commission-financial-report/beneficiaries/{bko.json()['id']}",
        params=period,
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["items"][0]["source"] == "MANUAL"
    assert detail.json()["items"][0]["strategy"] == "BKO"

    exported_pdf = await cliente.get(
        "/api/v1/commission-financial-report/export.pdf", params=period
    )
    assert exported_pdf.status_code == 200, exported_pdf.text
    assert exported_pdf.headers["content-type"] == "application/pdf"
    assert exported_pdf.content.startswith(b"%PDF-")

    exported_xlsx = await cliente.get(
        "/api/v1/commission-financial-report/export.xlsx", params=period
    )
    assert exported_xlsx.status_code == 200, exported_xlsx.text
    assert exported_xlsx.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert exported_xlsx.content.startswith(b"PK")

    next_period = {"period_start": "2026-08-14", "period_end": "2026-08-20"}
    next_generated = await cliente.post(
        "/api/v1/commission-settlements/generation", json=next_period, headers=csrf
    )
    assert next_generated.status_code == 200, next_generated.text
    next_settlement = next_generated.json()["items"][0]
    assert next_settlement["gross_amount"] == "0.00"
    assert next_settlement["carryover_amount"] == "30.00"
    assert next_settlement["payable_amount"] == "30.00"


async def test_excecao_individual_e_periodo_fechado_sao_versionados(
    cliente: AsyncClient, admin_semeado: dict[str, str]
) -> None:
    csrf = await _login_admin(cliente, admin_semeado)
    hoje = SystemClock(get_settings().app.app_timezone).business_date()
    company = await cliente.post(
        "/api/v1/companies",
        json={"legal_name": "Empresa Regras", "trade_name": "Regras"},
        headers=csrf,
    )
    consultant = await cliente.post(
        "/api/v1/collaborators",
        json={
            "company_id": company.json()["id"],
            "unit_id": None,
            "full_name": "Consultora com Override",
            "document": "529.982.247-25",
            "tax_regime": "CLT",
            "roles": [{"role": "CONSULTOR", "valid_from": "2026-01-01"}],
        },
        headers=csrf,
    )
    policy = await cliente.post(
        "/api/v1/commission-beneficiary-policies",
        json={
            "collaborator_id": consultant.json()["id"],
            "valid_from": hoje.isoformat(),
            "excluded": False,
            "override_tps_35_percentage": "13.5",
            "reason": "Acordo individual aprovado",
        },
        headers=csrf,
    )
    assert policy.status_code == 201, policy.text
    listed = await cliente.get("/api/v1/commission-beneficiary-policies")
    assert listed.json()[0]["override_tps_35_percentage"] == "13.500000"

    period = await cliente.post(
        "/api/v1/commission-periods",
        json={
            "period_start": "2026-08-01",
            "period_end": "2026-08-06",
            "cutoff_at": "2026-08-06T23:59:00-03:00",
            "reason": "Semana operacional",
        },
        headers=csrf,
    )
    assert period.status_code == 201, period.text
    closed = await cliente.post(
        f"/api/v1/commission-periods/{period.json()['id']}/closure",
        json={"reason": "Conferência concluída"},
        headers=csrf,
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "CLOSED"
    blocked = await cliente.post(
        "/api/v1/commission-settlements/generation",
        json={"period_start": "2026-08-01", "period_end": "2026-08-06"},
        headers=csrf,
    )
    assert blocked.status_code == 422
    assert "fechado" in blocked.json()["detail"].lower()


async def test_finalizacao_aceita_bonus_manual_e_exibe_separado_do_bruto(
    cliente: AsyncClient, admin_semeado: dict[str, str]
) -> None:
    csrf = await _login_admin(cliente, admin_semeado)
    company = await cliente.post(
        "/api/v1/companies",
        json={"legal_name": "Empresa Finalização", "trade_name": "Finalização"},
        headers=csrf,
    )
    finalizer = await cliente.post(
        "/api/v1/collaborators",
        json={
            "company_id": company.json()["id"],
            "unit_id": None,
            "full_name": "Finalizadora Manual",
            "document": "390.533.447-05",
            "tax_regime": "CLT",
            "roles": [{"role": "FINALIZACAO", "valid_from": "2026-01-01"}],
        },
        headers=csrf,
    )
    assert finalizer.status_code == 201, finalizer.text

    manual = await cliente.post(
        "/api/v1/commission-finalization-entries",
        json={
            "beneficiary_id": finalizer.json()["id"],
            "amount": "300.00",
            "effective_date": "2026-08-14",
            "description": "Bônus de finalização",
        },
        headers={**csrf, "Idempotency-Key": "finalization-bonus-test"},
    )
    assert manual.status_code == 201, manual.text

    generated = await cliente.post(
        "/api/v1/commission-settlements/generation",
        json={"period_start": "2026-08-14", "period_end": "2026-08-20"},
        headers=csrf,
    )
    assert generated.status_code == 200, generated.text
    settlement = next(
        item
        for item in generated.json()["items"]
        if item["beneficiary_id"] == finalizer.json()["id"]
    )
    assert settlement["gross_amount"] == "0.00"
    assert settlement["bonus_amount"] == "300.00"
    assert settlement["payable_amount"] == "300.00"

    report = await cliente.get(
        "/api/v1/commission-financial-report",
        params={"period_start": "2026-08-14", "period_end": "2026-08-20"},
    )
    assert report.status_code == 200, report.text
    assert report.json()["summary"]["finalization_commissions"] == "300.00"
    assert report.json()["summary"]["total_commissions"] == "300.00"


async def test_reabertura_de_periodo_exige_motivo_e_para_no_fechamento_pago(
    cliente: AsyncClient, admin_semeado: dict[str, str]
) -> None:
    csrf = await _login_admin(cliente, admin_semeado)
    company = await cliente.post(
        "/api/v1/companies",
        json={"legal_name": "Empresa Reabertura", "trade_name": "Reabertura"},
        headers=csrf,
    )
    bko = await cliente.post(
        "/api/v1/collaborators",
        json={
            "company_id": company.json()["id"],
            "unit_id": None,
            "full_name": "BKO da Reabertura",
            "document": "168.995.350-09",
            "tax_regime": "MEI",
            "roles": [{"role": "BKO", "valid_from": "2026-01-01"}],
        },
        headers=csrf,
    )
    assert bko.status_code == 201, bko.text

    period = await cliente.post(
        "/api/v1/commission-periods",
        json={
            "period_start": "2026-08-07",
            "period_end": "2026-08-13",
            "cutoff_at": "2026-08-13T23:59:00-03:00",
            "reason": "Semana operacional",
        },
        headers=csrf,
    )
    assert period.status_code == 201, period.text
    period_id = period.json()["id"]
    closed = await cliente.post(
        f"/api/v1/commission-periods/{period_id}/closure",
        json={"reason": "Conferência concluída"},
        headers=csrf,
    )
    assert closed.status_code == 200, closed.text

    # o motivo é obrigatório e precisa ser descritivo: reabrir é ato excepcional
    sem_motivo = await cliente.post(
        f"/api/v1/commission-periods/{period_id}/reopening",
        json={"reason": "erro"},
        headers=csrf,
    )
    assert sem_motivo.status_code == 422

    reopened = await cliente.post(
        f"/api/v1/commission-periods/{period_id}/reopening",
        json={"reason": "Recebimento conferido fora do prazo pelo Financeiro"},
        headers=csrf,
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["status"] == "OPEN"
    assert reopened.json()["reopened_at"] is not None
    assert reopened.json()["reopen_reason"] == (
        "Recebimento conferido fora do prazo pelo Financeiro"
    )
    assert reopened.json()["closed_at"] is not None

    # reaberto, o período volta a aceitar geração de fechamento
    manual = await cliente.post(
        "/api/v1/commission-bko-entries",
        json={
            "beneficiary_id": bko.json()["id"],
            "amount": "100.00",
            "effective_date": "2026-08-10",
            "description": "Lançamento que faltava",
        },
        headers={**csrf, "Idempotency-Key": "bko-reopening-test"},
    )
    assert manual.status_code == 201, manual.text
    generated = await cliente.post(
        "/api/v1/commission-settlements/generation",
        json={"period_start": "2026-08-07", "period_end": "2026-08-13"},
        headers=csrf,
    )
    assert generated.status_code == 200, generated.text
    settlement = generated.json()["items"][0]

    # depois de pago, a correção é por compensação, não por reabertura
    paid = await cliente.post(
        f"/api/v1/commission-settlements/{settlement['id']}/payments",
        json={
            "amount": settlement["payable_amount"],
            "payment_date": "2026-08-14",
            "payment_method": "PIX",
            "reference": "PIX-REABERTURA",
        },
        headers=csrf,
    )
    assert paid.status_code == 200, paid.text
    await cliente.post(
        f"/api/v1/commission-periods/{period_id}/closure",
        json={"reason": "Conferência refeita"},
        headers=csrf,
    )
    bloqueado = await cliente.post(
        f"/api/v1/commission-periods/{period_id}/reopening",
        json={"reason": "Tentativa de reabrir período já pago"},
        headers=csrf,
    )
    assert bloqueado.status_code == 409, bloqueado.text
    assert "pago" in bloqueado.json()["detail"].lower()
