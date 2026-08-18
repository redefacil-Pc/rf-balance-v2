"""Prévia da comissão enquanto a proposta está sendo digitada.

Existe para o operador conferir o número antes de salvar, como fazia o v1. Usa
os **mesmos** carregadores de regra e os mesmos calculadores de domínio do
cálculo efetivo: reimplementar a conta aqui — ou pior, na tela — criaria um
segundo cálculo que diverge do primeiro no dia em que alguém publicar uma versão
nova de regra.

Duas honestidades embutidas na resposta:

- a prévia assume **recebimento integral** da comissão da empresa. É o caso
  normal; num pagamento parcial a comissão sai proporcional, e menor.
- no Consultor Escalonado o percentual depende da produção acumulada no mês e da
  ordem em que os recebimentos forem reconhecidos. Ali a prévia é **estimativa**,
  e a resposta diz isso em vez de deixar a tela adivinhar.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commercial.domain.value_objects.percentual_tps import PercentualTps
from app.modules.commissions.application.rule_loading import (
    aplicar_excecao_individual,
    configuracao_de_estrategia,
    faixas_do_consultor_padrao,
    politica_do_beneficiario,
)
from app.modules.commissions.application.scaled_commission_engine import (
    ScaledCommissionEngine,
    interpretar_configuracao_escalonada,
)
from app.modules.commissions.domain.scaled_consultant import calcular_consultor_escalonado
from app.modules.commissions.domain.standard_consultant import calcular_consultor_padrao
from app.modules.organization.infrastructure.models.collaborator_role_model import (
    CollaboratorRoleModel,
)
from app.shared.domain.dinheiro import Dinheiro

PADRAO = "STANDARD_CONSULTANT"
ESCALONADO = "SCALED_CONSULTANT"
EXCLUIDO = "Este consultor está excluído do comissionamento por exceção individual."


@dataclass(frozen=True, slots=True)
class PreviaDeComissao:
    company_commission_amount: Decimal
    consultant_commission_amount: Decimal | None
    strategy: str | None
    #: verdadeiro quando o valor ainda pode mudar até o reconhecimento
    estimate: bool
    #: explicação para a tela exibir; `None` quando não há ressalva
    note: str | None


class PreviewCommissionHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(
        self,
        *,
        consultant_id: int,
        business_date: date,
        operation_amount: Decimal,
        tps_percentage: Decimal,
    ) -> PreviaDeComissao:
        # mesmo value object que a proposta usa para gravar: a prévia não pode
        # arredondar diferente do valor que será persistido
        comissao = PercentualTps.de(tps_percentage).aplicar_sobre(Dinheiro.de(operation_amount))
        vazia = PreviaDeComissao(
            company_commission_amount=comissao.valor,
            consultant_commission_amount=None,
            strategy=None,
            estimate=False,
            note=None,
        )
        if comissao.valor <= 0:
            return vazia

        papel = await self._papel_vigente(consultant_id, business_date)
        if papel is None:
            return replace(
                vazia, note="Este consultor não tem função de consultor vigente nessa data."
            )

        try:
            if papel == "CONSULTOR_MEI_ESCALONADO":
                return await self._escalonado(
                    consultant_id, business_date, operation_amount, tps_percentage, comissao.valor
                )
            return await self._padrao(
                consultant_id, business_date, operation_amount, tps_percentage, comissao.valor
            )
        except RuntimeError as erro:
            # não há regra ativa na data: a tela mostra o motivo em vez de um zero
            return replace(vazia, note=str(erro))

    async def _padrao(
        self,
        consultant_id: int,
        business_date: date,
        operation_amount: Decimal,
        tps: Decimal,
        comissao_empresa: Decimal,
    ) -> PreviaDeComissao:
        # a função CONSULTOR escolhe o motor padrão; MEI/CLT é regime cadastral
        _, faixas = await faixas_do_consultor_padrao(self._session, PADRAO, business_date, "MEI")
        policy = await politica_do_beneficiario(self._session, consultant_id, business_date)
        faixas, excluido = aplicar_excecao_individual(faixas, policy, tps)
        if excluido:
            return PreviaDeComissao(
                company_commission_amount=comissao_empresa,
                consultant_commission_amount=Decimal("0.00"),
                strategy=PADRAO,
                estimate=False,
                note=EXCLUIDO,
            )
        calculo = calcular_consultor_padrao(
            valor_operacao=operation_amount,
            comissao_empresa=comissao_empresa,
            tps=tps,
            valor_recebido_elegivel=comissao_empresa,
            regime="MEI",
            faixas=faixas,
        )
        return PreviaDeComissao(
            company_commission_amount=comissao_empresa,
            consultant_commission_amount=calculo.valor,
            strategy=PADRAO,
            estimate=False,
            note=None,
        )

    async def _escalonado(
        self,
        consultant_id: int,
        business_date: date,
        operation_amount: Decimal,
        tps: Decimal,
        comissao_empresa: Decimal,
    ) -> PreviaDeComissao:
        config = await configuracao_de_estrategia(self._session, ESCALONADO, business_date)
        policy = await politica_do_beneficiario(self._session, consultant_id, business_date)
        if policy is not None and policy.excluded:
            return PreviaDeComissao(
                company_commission_amount=comissao_empresa,
                consultant_commission_amount=Decimal("0.00"),
                strategy=ESCALONADO,
                estimate=False,
                note=EXCLUIDO,
            )

        acumulada = await ScaledCommissionEngine(
            self._session, outbox=None
        ).producao_acumulada_no_mes(consultant_id, business_date)
        faixas_producao, faixas_tps = interpretar_configuracao_escalonada(config.config)
        calculo = calcular_consultor_escalonado(
            valor_operacao=operation_amount,
            comissao_empresa_total=comissao_empresa,
            valor_recebido_elegivel=comissao_empresa,
            tps=tps,
            producao_anterior=acumulada,
            faixas_producao=faixas_producao,
            faixas_tps=faixas_tps,
        )
        return PreviaDeComissao(
            company_commission_amount=comissao_empresa,
            consultant_commission_amount=calculo.comissao,
            strategy=ESCALONADO,
            estimate=True,
            note=(
                "Estimativa: no Consultor Escalonado o percentual depende da produção "
                "acumulada no mês e da ordem em que os recebimentos forem reconhecidos. "
                f"Produção já reconhecida em {business_date.strftime('%m/%Y')}: "
                f"R$ {acumulada:.2f}."
            ),
        )

    async def _papel_vigente(self, collaborator_id: int, data: date) -> str | None:
        papel: str | None = await self._session.scalar(
            select(CollaboratorRoleModel.role)
            .where(
                CollaboratorRoleModel.collaborator_id == collaborator_id,
                CollaboratorRoleModel.role.in_(("CONSULTOR", "CONSULTOR_MEI_ESCALONADO")),
                CollaboratorRoleModel.valid_from <= data,
                or_(
                    CollaboratorRoleModel.valid_to.is_(None),
                    CollaboratorRoleModel.valid_to >= data,
                ),
            )
            .order_by(CollaboratorRoleModel.valid_from.desc())
            .limit(1)
        )
        return papel
