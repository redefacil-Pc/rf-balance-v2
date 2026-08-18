"""Cálculos puros das estratégias coletivas de comissão.

Os motores persistentes calculam o *delta* entre o direito antes e depois de
cada recebimento. Isso torna as faixas progressivas compatíveis com uma razão
imutável e permite recalcular o período quando há estorno.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")
CEM = Decimal("100")


def dinheiro(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def comissao_lider_comercial(
    *, base_recebida: Decimal, tps: Decimal, regime: str, configuracao: dict[str, object]
) -> tuple[Decimal, Decimal]:
    percentual = Decimal(str(configuracao[f"{regime.lower()}_percentage"]))
    if regime == "MEI" and tps < Decimal(str(configuracao["mei_min_tps"])):
        percentual = Decimal("0")
    return percentual, dinheiro(base_recebida * percentual / CEM)


@dataclass(frozen=True, slots=True)
class SegmentoProgressivo:
    minimo: Decimal
    maximo: Decimal
    base: Decimal
    percentual: Decimal
    comissao: Decimal


def comissao_progressiva(
    producao: Decimal, *, percentual_base: Decimal, faixas: list[dict[str, object]]
) -> tuple[Decimal, tuple[SegmentoProgressivo, ...]]:
    segmentos: list[SegmentoProgressivo] = []
    total = Decimal("0")
    for faixa in faixas:
        minimo = Decimal(str(faixa["min"]))
        maximo = Decimal(str(faixa["max"]))
        parcela = max(min(producao, maximo) - minimo, Decimal("0"))
        if parcela <= 0:
            continue
        percentual = Decimal(str(faixa["percentage"]))
        base = dinheiro(parcela * percentual_base / CEM)
        valor = dinheiro(base * percentual / CEM)
        total += valor
        segmentos.append(SegmentoProgressivo(minimo, maximo, base, percentual, valor))
    return dinheiro(total), tuple(segmentos)


def comissao_finalizador(base: Decimal, configuracao: dict[str, object]) -> Decimal:
    limite = Decimal(str(configuracao["threshold_amount"]))
    if base < limite:
        return Decimal("0.00")
    fixo = Decimal(str(configuracao["fixed_amount"]))
    excedente = Decimal(str(configuracao["excess_percentage"]))
    return dinheiro(fixo + (base - limite) * excedente / CEM)


def comissao_lider_finalizacao(
    base: Decimal, *, regime: str, configuracao: dict[str, object]
) -> tuple[Decimal, Decimal]:
    percentual = Decimal(str(configuracao[f"{regime.lower()}_percentage"]))
    return percentual, dinheiro(base * percentual / CEM)
