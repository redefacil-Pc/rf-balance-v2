"""Fluxos de estabilização que fecham a F2 antes de iniciar recebíveis."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient, Response

from app.platform.config.security import CSRF_COOKIE, CSRF_HEADER

pytestmark = pytest.mark.integration


class Api:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    @property
    def csrf(self) -> dict[str, str]:
        return {CSRF_HEADER: self.client.cookies[CSRF_COOKIE]}

    async def post(self, path: str, body: dict[str, Any]) -> Response:
        return await self.client.post(path, json=body, headers=self.csrf)

    async def put(self, path: str, body: dict[str, Any]) -> Response:
        return await self.client.put(path, json=body, headers=self.csrf)

    async def get(self, path: str, **params: Any) -> Response:
        return await self.client.get(path, params=params or None)


@pytest.fixture
async def api(cliente: AsyncClient, admin_semeado: dict[str, str]) -> Api:
    login = await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )
    assert login.status_code == 200
    return Api(cliente)


async def _company(api: Api) -> int:
    response = await api.post(
        "/api/v1/companies",
        {
            "legal_name": "Empresa Estável LTDA",
            "trade_name": "Estável",
            "document": "04.252.011/0001-10",
        },
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


async def test_cruds_administrativos_preservam_historico(api: Api) -> None:
    company_id = await _company(api)
    unit = await api.post(
        "/api/v1/units", {"company_id": company_id, "code": "MATRIZ", "name": "Matriz"}
    )
    assert unit.status_code == 201
    unit_id = int(unit.json()["id"])

    assert (
        await api.put(
            f"/api/v1/companies/{company_id}",
            {"legal_name": "Empresa Estável Atualizada LTDA", "trade_name": "Estável 2"},
        )
    ).status_code == 204
    assert (
        await api.put(f"/api/v1/units/{unit_id}", {"code": "SEDE", "name": "Sede"})
    ).status_code == 204
    assert (
        await api.put(f"/api/v1/units/{unit_id}/status", {"is_active": False})
    ).status_code == 204
    all_units = await api.get("/api/v1/units", company_id=company_id, only_active=False)
    assert all_units.json()[0]["code"] == "SEDE"
    assert all_units.json()[0]["is_active"] is False

    collaborator = await api.post(
        "/api/v1/collaborators",
        {
            "company_id": company_id,
            "unit_id": None,
            "full_name": "Pessoa Financeira",
            "document": "529.982.247-25",
            "tax_regime": "MEI",
            "roles": [{"role": "CONSULTOR", "valid_from": "2026-01-01"}],
            "email": "pessoa@empresa.test",
            "phone": "11999990000",
            "payment_key": {"key_type": "EMAIL", "key": "pix@empresa.test"},
        },
    )
    assert collaborator.status_code == 201, collaborator.text
    collaborator_id = int(collaborator.json()["id"])
    update = await api.put(
        f"/api/v1/collaborators/{collaborator_id}",
        {
            "company_id": company_id,
            "unit_id": None,
            "full_name": "Pessoa Atualizada",
            "tax_regime": "MEI",
            "email": "nova@empresa.test",
            "phone": "11888880000",
            "payment_key": {"key_type": "TELEFONE", "key": "+5511888880000"},
        },
    )
    assert update.status_code == 204, update.text
    details = await api.get(f"/api/v1/collaborators/{collaborator_id}/details")
    assert details.json()["email"] == "nova@empresa.test"
    assert details.json()["payment_key_type"] == "TELEFONE"

    leader = await api.post(
        "/api/v1/collaborators",
        {
            "company_id": company_id,
            "unit_id": None,
            "full_name": "Líder do Histórico",
            "document": "111.444.777-35",
            "tax_regime": "CLT",
            "roles": [{"role": "LIDER", "valid_from": "2026-01-01"}],
        },
    )
    assert leader.status_code == 201, leader.text
    assignment = await api.post(
        "/api/v1/assignments",
        {
            "consultant_id": collaborator_id,
            "leader_id": leader.json()["id"],
            "assignment_type": "COMERCIAL",
            "start_date": "2026-01-10",
            "reason": "estrutura inicial",
        },
    )
    assert assignment.status_code == 201, assignment.text
    closed = await api.put(
        f"/api/v1/assignments/{assignment.json()['id']}/closure",
        {"end_date": "2026-08-13", "reason": "reorganização de equipe"},
    )
    assert closed.status_code == 204, closed.text
    history = await api.get(f"/api/v1/assignments/consultant/{collaborator_id}")
    assert history.json()[0]["end_date"] == "2026-08-13"


async def test_usuario_colaborador_proposta_comprovante_e_aprovacao(
    api: Api, novo_cliente: Any
) -> None:
    company_id = await _company(api)
    consultant = await api.post(
        "/api/v1/users",
        {
            "email": "consultora.fluxo@rfbalance.test",
            "full_name": "Consultora do Fluxo",
            "roles": ["CONSULTOR"],
            "collaborator": {
                "company_id": company_id,
                "unit_id": None,
                "document": "529.982.247-25",
                "tax_regime": "MEI",
                "function": "CONSULTOR",
                "valid_from": "2026-01-01",
            },
        },
    )
    operational = await api.post(
        "/api/v1/users",
        {
            "email": "operacao.fluxo@rfbalance.test",
            "full_name": "Operação do Fluxo",
            "roles": ["OPERACIONAL"],
            "collaborator": {
                "company_id": company_id,
                "unit_id": None,
                "document": "111.444.777-35",
                "tax_regime": "CLT",
                "function": "FINALIZACAO",
                "valid_from": "2026-01-01",
            },
        },
    )
    finance = await api.post(
        "/api/v1/users",
        {
            "email": "financeiro.fluxo@rfbalance.test",
            "full_name": "Financeiro do Fluxo",
            "roles": ["FINANCEIRO"],
        },
    )
    assert consultant.status_code == operational.status_code == finance.status_code == 201
    consultant_id = int(consultant.json()["collaborator_id"])

    async with novo_cliente() as operational_client:
        login = await operational_client.post(
            "/api/v1/auth/login",
            json={
                "email": "operacao.fluxo@rfbalance.test",
                "password": operational.json()["temporary_password"],
            },
        )
        assert login.status_code == 200
        csrf = {CSRF_HEADER: operational_client.cookies[CSRF_COOKIE]}
        proposal = await operational_client.post(
            "/api/v1/proposals",
            json={
                "consultant_id": consultant_id,
                "business_date": "2026-08-13",
                "customer_name": "Cliente Integrado",
                "customer_document": "111.444.777-35",
                "operation_amount": "2500.00",
                "tps_percentage": "10",
            },
            headers=csrf,
        )
        assert proposal.status_code == 201, proposal.text
        proposal_id = int(proposal.json()["id"])
        upload = await operational_client.post(
            f"/api/v1/proposals/{proposal_id}/attachments",
            files={"file": ("comprovante.pdf", b"%PDF-1.4 fluxo integrado", "application/pdf")},
            headers=csrf,
        )
        assert upload.status_code == 201, upload.text

        # A Finalização declara o valor recebido **antes** de enviar: é
        # justamente isso que o Financeiro vai conferir no extrato.
        assert "receipts:write" in login.json()["permissions"]
        receipt = await operational_client.post(
            f"/api/v1/proposals/{proposal_id}/receipts",
            data={
                "amount": "100.00",
                "business_date": "2026-08-13",
                "payment_method": "PIX",
                "reference": "E2E-001",
            },
            files={"proof": ("recebimento.pdf", b"%PDF-1.4 receipt", "application/pdf")},
            headers={**csrf, "Idempotency-Key": "receipt-flow-001"},
        )
        assert receipt.status_code == 201, receipt.text
        assert receipt.json()["status"] == "SUBMITTED"
        receipt_id = int(receipt.json()["id"])
        replay = await operational_client.post(
            f"/api/v1/proposals/{proposal_id}/receipts",
            data={
                "amount": "100.00",
                "business_date": "2026-08-13",
                "payment_method": "PIX",
                "reference": "E2E-001",
            },
            files={"proof": ("recebimento.pdf", b"%PDF-1.4 receipt", "application/pdf")},
            headers={**csrf, "Idempotency-Key": "receipt-flow-001"},
        )
        assert replay.status_code == 201, replay.text
        assert replay.json()["id"] == receipt_id

        submitted = await operational_client.post(
            f"/api/v1/proposals/{proposal_id}/submission",
            json={"version": proposal.json()["version"]},
            headers=csrf,
        )
        assert submitted.status_code == 200

    async with novo_cliente() as finance_client:
        login = await finance_client.post(
            "/api/v1/auth/login",
            json={
                "email": "financeiro.fluxo@rfbalance.test",
                "password": finance.json()["temporary_password"],
            },
        )
        assert login.status_code == 200
        csrf = {CSRF_HEADER: finance_client.cookies[CSRF_COOKIE]}

        # uma decisão só: aprovar a proposta é conferir o pagamento e
        # reconhecer o dinheiro no mesmo ato
        approved = await finance_client.post(
            f"/api/v1/proposals/{proposal_id}/decision",
            json={"version": submitted.json()["version"], "decision": "APROVAR"},
            headers=csrf,
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["approval_status"] == "APPROVED"

        detalhe = await finance_client.get(f"/api/v1/proposals/{proposal_id}")
        assert detalhe.json()["paid_amount"] == "100.00"
        assert detalhe.json()["status"] == "PARTIALLY_PAID"

        reversal = await finance_client.post(
            f"/api/v1/receipts/{receipt_id}/reversal",
            json={"reason": "lançamento duplicado", "business_date": "2026-08-13"},
            headers=csrf,
        )
        assert reversal.status_code == 200, reversal.text
        assert reversal.json()["proposal_status"] == "OPEN"
        assert reversal.json()["proposal_paid_amount"] == "0.00"
