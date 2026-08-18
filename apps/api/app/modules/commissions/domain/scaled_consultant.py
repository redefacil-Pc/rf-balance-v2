"""Cálculo marginal determinístico do Consultor Escalonado."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")
CEM = Decimal("100")


class ConfiguracaoEscalonadaInvalidaError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class FaixaTpsEscalonada:
    minimo: Decimal
    maximo: Decimal | None

    def contem(self, tps: Decimal) -> bool:
        return tps >= self.minimo and (self.maximo is None or tps < self.maximo)


@dataclass(frozen=True, slots=True)
class FaixaProducaoEscalonada:
    minimo: Decimal
    maximo: Decimal | None
    percentuais: tuple[Decimal, ...]


@dataclass(frozen=True, slots=True)
class SegmentoEscalonado:
    faixa_minimo: Decimal
    faixa_maximo: Decimal | None
    producao: Decimal
    percentual: Decimal
    comissao_empresa: Decimal
    comissao_consultor: Decimal


@dataclass(frozen=True, slots=True)
class CalculoConsultorEscalonado:
    producao_anterior: Decimal
    producao_reconhecida: Decimal
    producao_posterior: Decimal
    comissao: Decimal
    segmentos: tuple[SegmentoEscalonado, ...]


def validar_configuracao_escalonada(
    faixas_producao: tuple[FaixaProducaoEscalonada, ...],
    faixas_tps: tuple[FaixaTpsEscalonada, ...],
) -> None:
    if not faixas_producao or not faixas_tps:
        raise ConfiguracaoEscalonadaInvalidaError("Informe faixas de produção e TPS.")
    esperada = Decimal("0")
    for indice, faixa in enumerate(faixas_producao):
        if faixa.minimo != esperada:
            raise ConfiguracaoEscalonadaInvalidaError(
                f"Há lacuna ou sobreposição na produção em {esperada}."
            )
        if len(faixa.percentuais) != len(faixas_tps):
            raise ConfiguracaoEscalonadaInvalidaError(
                "Cada faixa de produção deve possuir um percentual para cada faixa TPS."
            )
        if any(item < 0 or item > 100 for item in faixa.percentuais):
            raise ConfiguracaoEscalonadaInvalidaError("Percentual deve estar entre 0 e 100.")
        ultima = indice == len(faixas_producao) - 1
        if ultima and faixa.maximo is not None:
            raise ConfiguracaoEscalonadaInvalidaError(
                "A última faixa de produção deve ficar sem limite."
            )
        if not ultima:
            if faixa.maximo is None or faixa.maximo <= faixa.minimo:
                raise ConfiguracaoEscalonadaInvalidaError("Limite de produção inválido.")
            esperada = faixa.maximo

    ordenadas = sorted(faixas_tps, key=lambda item: item.minimo)
    esperada = Decimal("0")
    for indice, faixa_tps in enumerate(ordenadas):
        if faixa_tps.minimo != esperada:
            raise ConfiguracaoEscalonadaInvalidaError(
                f"Há lacuna ou sobreposição nas faixas TPS em {esperada}."
            )
        ultima = indice == len(ordenadas) - 1
        if ultima and faixa_tps.maximo is not None:
            raise ConfiguracaoEscalonadaInvalidaError("A última faixa TPS deve ficar sem limite.")
        if not ultima:
            if faixa_tps.maximo is None or faixa_tps.maximo <= faixa_tps.minimo:
                raise ConfiguracaoEscalonadaInvalidaError("Limite TPS inválido.")
            esperada = faixa_tps.maximo


def calcular_consultor_escalonado(
    *,
    valor_operacao: Decimal,
    comissao_empresa_total: Decimal,
    valor_recebido_elegivel: Decimal,
    tps: Decimal,
    producao_anterior: Decimal,
    faixas_producao: tuple[FaixaProducaoEscalonada, ...],
    faixas_tps: tuple[FaixaTpsEscalonada, ...],
) -> CalculoConsultorEscalonado:
    validar_configuracao_escalonada(faixas_producao, faixas_tps)
    if valor_operacao <= 0 or comissao_empresa_total <= 0 or valor_recebido_elegivel <= 0:
        raise ValueError("As bases do cálculo devem ser positivas.")
    if tps < 0 or tps > 100 or producao_anterior < 0:
        raise ValueError("TPS e produção acumulada devem ser válidos.")

    indice_tps = next(
        (indice for indice, faixa in enumerate(faixas_tps) if faixa.contem(tps)), None
    )
    if indice_tps is None:
        raise ConfiguracaoEscalonadaInvalidaError(f"Nenhuma faixa TPS cobre {tps}.")

    base = min(valor_recebido_elegivel, comissao_empresa_total)
    producao = (valor_operacao * base / comissao_empresa_total).quantize(
        CENTAVO, rounding=ROUND_HALF_UP
    )
    inicio = producao_anterior
    fim = inicio + producao
    segmentos: list[SegmentoEscalonado] = []
    for faixa in faixas_producao:
        limite = faixa.maximo if faixa.maximo is not None else fim
        inicio_segmento = max(inicio, faixa.minimo)
        fim_segmento = min(fim, limite)
        if fim_segmento <= inicio_segmento:
            continue
        producao_segmento = (fim_segmento - inicio_segmento).quantize(
            CENTAVO, rounding=ROUND_HALF_UP
        )
        percentual = faixa.percentuais[indice_tps]
        empresa = (producao_segmento * tps / CEM).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        consultor = (empresa * percentual / CEM).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        segmentos.append(
            SegmentoEscalonado(
                faixa_minimo=faixa.minimo,
                faixa_maximo=faixa.maximo,
                producao=producao_segmento,
                percentual=percentual,
                comissao_empresa=empresa,
                comissao_consultor=consultor,
            )
        )
    if sum((item.producao for item in segmentos), Decimal("0")) != producao:
        raise ConfiguracaoEscalonadaInvalidaError(
            "As faixas de produção não cobrem toda a produção reconhecida."
        )
    return CalculoConsultorEscalonado(
        producao_anterior=inicio.quantize(CENTAVO, rounding=ROUND_HALF_UP),
        producao_reconhecida=producao,
        producao_posterior=fim.quantize(CENTAVO, rounding=ROUND_HALF_UP),
        comissao=sum((item.comissao_consultor for item in segmentos), Decimal("0")),
        segmentos=tuple(segmentos),
    )
