"""Resolução da regra vigente numa data.

Os motores e a prévia do cadastro precisam exatamente da mesma resposta para
"qual regra vale nesta data, para esta pessoa". Com a consulta duplicada, uma
mudança de critério de vigência passaria a valer só num dos lados — e o número
que o operador confere na tela deixaria de ser o número que o sistema paga.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commissions.domain.standard_consultant import FaixaConsultorPadrao
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionBeneficiaryPolicyModel,
    CommissionRuleModel,
    CommissionRuleSetModel,
    CommissionStrategyConfigModel,
)


async def politica_do_beneficiario(
    session: AsyncSession, collaborator_id: int, data: date
) -> CommissionBeneficiaryPolicyModel | None:
    """Exceção individual vigente, se houver. A mais recente vence."""
    policy: CommissionBeneficiaryPolicyModel | None = await session.scalar(
        select(CommissionBeneficiaryPolicyModel)
        .where(
            CommissionBeneficiaryPolicyModel.collaborator_id == collaborator_id,
            CommissionBeneficiaryPolicyModel.valid_from <= data,
            or_(
                CommissionBeneficiaryPolicyModel.valid_to.is_(None),
                CommissionBeneficiaryPolicyModel.valid_to >= data,
            ),
        )
        .order_by(CommissionBeneficiaryPolicyModel.valid_from.desc())
        .limit(1)
    )
    return policy


async def conjunto_de_regras(
    session: AsyncSession, estrategia: str, data: date
) -> CommissionRuleSetModel:
    conjunto = await session.scalar(
        select(CommissionRuleSetModel)
        .where(
            CommissionRuleSetModel.strategy == estrategia,
            CommissionRuleSetModel.status == "ACTIVE",
            CommissionRuleSetModel.valid_from <= data,
            or_(
                CommissionRuleSetModel.valid_to.is_(None),
                CommissionRuleSetModel.valid_to >= data,
            ),
        )
        .order_by(CommissionRuleSetModel.valid_from.desc(), CommissionRuleSetModel.id.desc())
        .limit(1)
    )
    if conjunto is None:
        raise RuntimeError(f"Não há regra {estrategia} ativa em {data.isoformat()}.")
    return conjunto


async def faixas_do_consultor_padrao(
    session: AsyncSession, estrategia: str, data: date, regime: str
) -> tuple[CommissionRuleSetModel, list[FaixaConsultorPadrao]]:
    conjunto = await conjunto_de_regras(session, estrategia, data)
    regras = list(
        (
            await session.scalars(
                select(CommissionRuleModel)
                .where(
                    CommissionRuleModel.rule_set_id == conjunto.id,
                    CommissionRuleModel.tax_regime == regime,
                    CommissionRuleModel.role == "CONSULTOR",
                )
                .order_by(CommissionRuleModel.sort_order)
            )
        ).all()
    )
    faixas = [
        FaixaConsultorPadrao(
            id=regra.id,
            regime=regra.tax_regime,
            tps_minimo=regra.tps_min,
            tps_maximo=regra.tps_max,
            percentual=regra.percentage,
        )
        for regra in regras
    ]
    return conjunto, faixas


async def configuracao_de_estrategia(
    session: AsyncSession, estrategia: str, data: date
) -> CommissionStrategyConfigModel:
    config = await session.scalar(
        select(CommissionStrategyConfigModel)
        .where(
            CommissionStrategyConfigModel.strategy == estrategia,
            CommissionStrategyConfigModel.status == "ACTIVE",
            CommissionStrategyConfigModel.valid_from <= data,
            or_(
                CommissionStrategyConfigModel.valid_to.is_(None),
                CommissionStrategyConfigModel.valid_to >= data,
            ),
        )
        .order_by(
            CommissionStrategyConfigModel.valid_from.desc(),
            CommissionStrategyConfigModel.id.desc(),
        )
        .limit(1)
    )
    if config is None:
        raise RuntimeError(f"Não há configuração {estrategia} ativa em {data.isoformat()}.")
    return config


def aplicar_excecao_individual(
    faixas: list[FaixaConsultorPadrao],
    policy: CommissionBeneficiaryPolicyModel | None,
    tps: Decimal,
) -> tuple[list[FaixaConsultorPadrao], bool]:
    """Devolve as faixas com a exceção aplicada e se o consultor está excluído.

    A exceção só troca o percentual da faixa que cobre o TPS da proposta: uma
    exceção não reescreve a tabela inteira, senão o consultor passaria a ter
    regra própria em todas as faixas sem ninguém ter decidido isso.
    """
    if policy is None:
        return faixas, False
    if policy.excluded:
        return faixas, True
    if tps >= Decimal("35") and policy.override_tps_35_percentage is not None:
        override = policy.override_tps_35_percentage
        return [
            faixa.__class__(
                id=faixa.id,
                regime=faixa.regime,
                tps_minimo=faixa.tps_minimo,
                tps_maximo=faixa.tps_maximo,
                percentual=override if faixa.contem(tps) else faixa.percentual,
            )
            for faixa in faixas
        ], False
    return faixas, False
