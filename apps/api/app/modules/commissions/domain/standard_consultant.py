"""Cálculo determinístico do consultor padrão MEI.

As faixas usam intervalos [mínimo, máximo), exceto a última, cujo máximo é
inclusivo. Dinheiro é arredondado somente na saída, por HALF_UP.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")


class ConfiguracaoDeComissaoInvalidaError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class FaixaConsultorPadrao:
    id: int
    regime: str
    tps_minimo: Decimal
    tps_maximo: Decimal | None
    percentual: Decimal

    def contem(self, tps: Decimal) -> bool:
        return tps >= self.tps_minimo and (self.tps_maximo is None or tps < self.tps_maximo)


@dataclass(frozen=True, slots=True)
class CalculoConsultorPadrao:
    regra_id: int
    percentual: Decimal
    base_elegivel: Decimal
    proporcao_recebida: Decimal
    producao_reconhecida: Decimal
    valor: Decimal


def validar_faixas(faixas: list[FaixaConsultorPadrao], regime: str) -> None:
    candidatas = sorted(
        (faixa for faixa in faixas if faixa.regime == regime),
        key=lambda faixa: faixa.tps_minimo,
    )
    if not candidatas or candidatas[0].tps_minimo != 0:
        raise ConfiguracaoDeComissaoInvalidaError(f"As faixas de {regime} devem iniciar em 0.")
    esperado = Decimal("0")
    for indice, faixa in enumerate(candidatas):
        if faixa.tps_minimo != esperado:
            raise ConfiguracaoDeComissaoInvalidaError(
                f"Há lacuna ou sobreposição nas faixas de {regime} em {esperado}."
            )
        if faixa.percentual < 0 or faixa.percentual > 100:
            raise ConfiguracaoDeComissaoInvalidaError("Percentual deve estar entre 0 e 100.")
        ultima = indice == len(candidatas) - 1
        if ultima:
            if faixa.tps_maximo is not None:
                raise ConfiguracaoDeComissaoInvalidaError("A última faixa não deve ter máximo.")
        else:
            if faixa.tps_maximo is None or faixa.tps_maximo <= faixa.tps_minimo:
                raise ConfiguracaoDeComissaoInvalidaError(
                    "Faixa intermediária possui limite inválido."
                )
            esperado = faixa.tps_maximo


def calcular_consultor_padrao(
    *,
    valor_operacao: Decimal,
    comissao_empresa: Decimal,
    tps: Decimal,
    valor_recebido_elegivel: Decimal,
    regime: str,
    faixas: list[FaixaConsultorPadrao],
) -> CalculoConsultorPadrao:
    validar_faixas(faixas, regime)
    if valor_operacao <= 0 or comissao_empresa <= 0 or valor_recebido_elegivel <= 0:
        raise ValueError("As bases do cálculo devem ser positivas.")
    if tps < 0 or tps > 100:
        raise ValueError("TPS deve estar entre 0 e 100.")
    regra = next((faixa for faixa in faixas if faixa.regime == regime and faixa.contem(tps)), None)
    if regra is None:
        raise ConfiguracaoDeComissaoInvalidaError(f"Nenhuma faixa de {regime} cobre TPS {tps}.")

    base = min(valor_recebido_elegivel, comissao_empresa)
    proporcao = base / comissao_empresa
    producao = (valor_operacao * proporcao).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    valor = (base * regra.percentual / Decimal("100")).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    return CalculoConsultorPadrao(
        regra_id=regra.id,
        percentual=regra.percentual,
        base_elegivel=base.quantize(CENTAVO, rounding=ROUND_HALF_UP),
        proporcao_recebida=proporcao,
        producao_reconhecida=producao,
        valor=valor,
    )
