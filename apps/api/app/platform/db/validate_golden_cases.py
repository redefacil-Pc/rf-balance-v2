"""Compara casos dourados CSV com as configurações financeiras ativas da v2.

Uso no ambiente local::

    python -m app.platform.db.validate_golden_cases

O comando é somente leitura. Casos manuais são registrados como ``SKIPPED``
porque representam valores informados pelo Financeiro, não uma fórmula do motor.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commercial.domain.policies import settlement_tolerance_policy as tolerancia
from app.modules.commercial.domain.value_objects.percentual_tps import PercentualTps
from app.modules.commissions.application.queries.preview_commission import ESCALONADO, PADRAO
from app.modules.commissions.application.rule_loading import (
    configuracao_de_estrategia,
    faixas_do_consultor_padrao,
)
from app.modules.commissions.application.scaled_commission_engine import (
    interpretar_configuracao_escalonada,
)
from app.modules.commissions.domain.group_commissions import comissao_lider_comercial
from app.modules.commissions.domain.scaled_consultant import calcular_consultor_escalonado
from app.modules.commissions.domain.standard_consultant import calcular_consultor_padrao
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes
from app.shared.domain.dinheiro import Dinheiro

ZERO = Decimal("0.00")
CENT = Decimal("0.01")
DEFAULT_INPUT = Path("/dados/homologacao/casos-dourados-v1.csv")
DEFAULT_OUTPUT = Path("/dados/homologacao-output/resultado-casos-dourados-v2.csv")

REQUIRED_FIELDS = {
    "case_id",
    "category",
    "v1_reference",
    "competence_date",
    "consultant_profile",
    "operation_amount",
    "received_amount",
    "tps_percent",
    "prior_month_production",
    "receipt_status",
    "reversal_amount",
    "leader_profile",
    "expected_consultant_commission",
    "expected_leadership_commission",
    "expected_finalization_commission",
    "expected_bko_commission",
    "expected_total_commission",
    "expected_proposal_status",
    "notes",
}

RESULT_FIELDS = (
    "v2_consultant_commission",
    "v2_leadership_commission",
    "v2_finalization_commission",
    "v2_bko_commission",
    "v2_total_commission",
    "v2_proposal_status",
    "consultant_difference",
    "leadership_difference",
    "total_difference",
    "validation_result",
    "validation_message",
)


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT)


@dataclass(frozen=True, slots=True)
class GoldenCase:
    case_id: str
    category: str
    competence_date: date
    consultant_profile: str
    operation_amount: Decimal
    received_amount: Decimal
    tps_percent: Decimal
    prior_month_production: Decimal
    receipt_status: str
    reversal_amount: Decimal
    leader_profile: str
    expected_consultant: Decimal
    expected_leadership: Decimal
    expected_finalization: Decimal
    expected_bko: Decimal
    expected_total: Decimal
    expected_status: str

    @classmethod
    def from_row(cls, row: dict[str, str]) -> GoldenCase:
        def decimal(field: str) -> Decimal:
            try:
                return Decimal(row[field]).quantize(CENT)
            except Exception as error:
                raise ValueError(f"{row.get('case_id', '?')}: {field} inválido") from error

        try:
            competence_date = date.fromisoformat(row["competence_date"])
        except Exception as error:
            raise ValueError(f"{row.get('case_id', '?')}: competence_date inválida") from error
        return cls(
            case_id=row["case_id"].strip(),
            category=row["category"].strip().upper(),
            competence_date=competence_date,
            consultant_profile=row["consultant_profile"].strip().upper(),
            operation_amount=decimal("operation_amount"),
            received_amount=decimal("received_amount"),
            tps_percent=decimal("tps_percent"),
            prior_month_production=decimal("prior_month_production"),
            receipt_status=row["receipt_status"].strip().upper(),
            reversal_amount=decimal("reversal_amount"),
            leader_profile=row["leader_profile"].strip().upper(),
            expected_consultant=decimal("expected_consultant_commission"),
            expected_leadership=decimal("expected_leadership_commission"),
            expected_finalization=decimal("expected_finalization_commission"),
            expected_bko=decimal("expected_bko_commission"),
            expected_total=decimal("expected_total_commission"),
            expected_status=row["expected_proposal_status"].strip().upper(),
        )


@dataclass(frozen=True, slots=True)
class CalculatedCase:
    consultant: Decimal
    leadership: Decimal
    finalization: Decimal
    bko: Decimal
    status: str

    @property
    def total(self) -> Decimal:
        return money(self.consultant + self.leadership + self.finalization + self.bko)


def recognized_amount(case: GoldenCase) -> Decimal:
    if case.receipt_status == "SUBMITTED":
        return ZERO
    return money(max(case.received_amount - case.reversal_amount, ZERO))


def proposal_status(*, company_commission: Decimal, received: Decimal) -> str:
    result = tolerancia.vigente().classificar(
        esperado=Dinheiro.de(company_commission), recebido=Dinheiro.de(received)
    )
    if result is tolerancia.ResultadoDeQuitacao.EM_ABERTO:
        return "OPEN" if received == ZERO else "PARTIALLY_PAID"
    return "PAID"


class GoldenCaseExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def calculate(self, case: GoldenCase) -> CalculatedCase | None:
        if case.category == "MANUAL":
            return None
        if case.operation_amount <= ZERO:
            raise ValueError("operação deve ser positiva em caso calculável")

        company = (
            PercentualTps.de(case.tps_percent)
            .aplicar_sobre(Dinheiro.de(case.operation_amount))
            .valor
        )
        recognized = recognized_amount(case)
        eligible = min(recognized, company)
        consultant = ZERO

        if eligible > ZERO:
            if case.consultant_profile == "CONSULTOR_MEI_ESCALONADO":
                config = await configuracao_de_estrategia(
                    self.session, ESCALONADO, case.competence_date
                )
                production_tiers, tps_tiers = interpretar_configuracao_escalonada(config.config)
                consultant = calcular_consultor_escalonado(
                    valor_operacao=case.operation_amount,
                    comissao_empresa_total=company,
                    valor_recebido_elegivel=eligible,
                    tps=case.tps_percent,
                    producao_anterior=case.prior_month_production,
                    faixas_producao=production_tiers,
                    faixas_tps=tps_tiers,
                ).comissao
            elif case.consultant_profile == "CONSULTOR":
                _, tiers = await faixas_do_consultor_padrao(
                    self.session, PADRAO, case.competence_date, "MEI"
                )
                consultant = calcular_consultor_padrao(
                    valor_operacao=case.operation_amount,
                    comissao_empresa=company,
                    tps=case.tps_percent,
                    valor_recebido_elegivel=eligible,
                    regime="MEI",
                    faixas=tiers,
                ).valor
            else:
                raise ValueError(f"perfil calculável desconhecido: {case.consultant_profile}")

        leadership = ZERO
        if case.leader_profile in {"LIDER_MEI", "LIDER_CLT"} and eligible > ZERO:
            config = await configuracao_de_estrategia(
                self.session, "COMMERCIAL_LEADER", case.competence_date
            )
            regime = "MEI" if case.leader_profile == "LIDER_MEI" else "CLT"
            _, leadership = comissao_lider_comercial(
                base_recebida=eligible,
                tps=case.tps_percent,
                regime=regime,
                configuracao=config.config,
            )
        elif case.leader_profile != "NONE":
            raise ValueError(f"perfil de liderança desconhecido: {case.leader_profile}")

        return CalculatedCase(
            consultant=money(consultant),
            leadership=money(leadership),
            finalization=ZERO,
            bko=ZERO,
            status=proposal_status(company_commission=company, received=recognized),
        )


def load_cases(path: Path) -> list[tuple[GoldenCase, dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fields = set(reader.fieldnames or ())
        missing = sorted(REQUIRED_FIELDS - fields)
        if missing:
            raise ValueError(f"CSV sem campos obrigatórios: {', '.join(missing)}")
        rows = [(GoldenCase.from_row(row), row) for row in reader]
    if not rows:
        raise ValueError("CSV não possui casos")
    identifiers = [case.case_id for case, _ in rows]
    duplicated = sorted({item for item in identifiers if identifiers.count(item) > 1})
    if duplicated:
        raise ValueError(f"case_id duplicado: {', '.join(duplicated)}")
    return rows


def result_row(
    original: dict[str, str], case: GoldenCase, calculated: CalculatedCase | None
) -> dict[str, str]:
    output = dict(original)
    if calculated is None:
        output.update({field: "" for field in RESULT_FIELDS})
        output["validation_result"] = "SKIPPED"
        output["validation_message"] = "Lançamento manual: validar pelo fluxo de fechamento."
        return output

    consultant_difference = money(calculated.consultant - case.expected_consultant)
    leadership_difference = money(calculated.leadership - case.expected_leadership)
    total_difference = money(calculated.total - case.expected_total)
    matching = (
        consultant_difference == ZERO
        and leadership_difference == ZERO
        and calculated.finalization == case.expected_finalization
        and calculated.bko == case.expected_bko
        and total_difference == ZERO
        and calculated.status == case.expected_status
    )
    output.update(
        {
            "v2_consultant_commission": f"{calculated.consultant:.2f}",
            "v2_leadership_commission": f"{calculated.leadership:.2f}",
            "v2_finalization_commission": f"{calculated.finalization:.2f}",
            "v2_bko_commission": f"{calculated.bko:.2f}",
            "v2_total_commission": f"{calculated.total:.2f}",
            "v2_proposal_status": calculated.status,
            "consultant_difference": f"{consultant_difference:.2f}",
            "leadership_difference": f"{leadership_difference:.2f}",
            "total_difference": f"{total_difference:.2f}",
            "validation_result": "PASS" if matching else "FAIL",
            "validation_message": "Valores coincidem." if matching else "Divergência encontrada.",
        }
    )
    return output


def error_row(original: dict[str, str], message: str) -> dict[str, str]:
    output = dict(original)
    output.update({field: "" for field in RESULT_FIELDS})
    output["validation_result"] = "ERROR"
    output["validation_message"] = message
    return output


async def execute(input_path: Path, output_path: Path) -> int:
    cases = load_cases(input_path)
    settings = get_settings()
    engine = criar_engine(settings.database)
    factory = criar_fabrica_de_sessoes(engine)
    results: list[dict[str, str]] = []
    try:
        async with factory() as session:
            executor = GoldenCaseExecutor(session)
            for case, original in cases:
                try:
                    calculated = await executor.calculate(case)
                    results.append(result_row(original, case, calculated))
                except Exception as error:
                    results.append(error_row(original, str(error)))
    finally:
        await engine.dispose()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(
            destination,
            fieldnames=[*cases[0][1].keys(), *RESULT_FIELDS],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(results)

    totals = {
        status: sum(item["validation_result"] == status for item in results)
        for status in ("PASS", "FAIL", "ERROR", "SKIPPED")
    }
    print(
        f"casos={len(results)} pass={totals['PASS']} fail={totals['FAIL']} "
        f"error={totals['ERROR']} skipped={totals['SKIPPED']}"
    )
    print(f"relatório={output_path}")
    return 1 if totals["FAIL"] or totals["ERROR"] else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        return asyncio.run(execute(args.input, args.output))
    except Exception as error:
        print(f"homologação não executada: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
