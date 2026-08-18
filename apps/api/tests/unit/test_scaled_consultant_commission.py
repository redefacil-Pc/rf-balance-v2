from decimal import Decimal

import pytest

from app.modules.commissions.domain.scaled_consultant import (
    FaixaProducaoEscalonada,
    FaixaTpsEscalonada,
    calcular_consultor_escalonado,
)


def _producao() -> tuple[FaixaProducaoEscalonada, ...]:
    return (
        FaixaProducaoEscalonada(
            Decimal("0"),
            Decimal("75000"),
            (Decimal("8"), Decimal("6"), Decimal("4"), Decimal("2")),
        ),
        FaixaProducaoEscalonada(
            Decimal("75000"),
            Decimal("175000"),
            (Decimal("10"), Decimal("8"), Decimal("6"), Decimal("4")),
        ),
        FaixaProducaoEscalonada(
            Decimal("175000"),
            None,
            (Decimal("11.5"), Decimal("9.5"), Decimal("7.5"), Decimal("5.5")),
        ),
    )


def _tps() -> tuple[FaixaTpsEscalonada, ...]:
    return (
        FaixaTpsEscalonada(Decimal("35"), None),
        FaixaTpsEscalonada(Decimal("30"), Decimal("35")),
        FaixaTpsEscalonada(Decimal("25"), Decimal("30")),
        FaixaTpsEscalonada(Decimal("0"), Decimal("25")),
    )


def _calcular(*, producao: str, anterior: str = "0", tps: str = "35"):
    valor = Decimal(producao)
    percentual = Decimal(tps)
    comissao_empresa = valor * percentual / Decimal("100")
    return calcular_consultor_escalonado(
        valor_operacao=valor,
        comissao_empresa_total=comissao_empresa,
        valor_recebido_elegivel=comissao_empresa,
        tps=percentual,
        producao_anterior=Decimal(anterior),
        faixas_producao=_producao(),
        faixas_tps=_tps(),
    )


def test_rateia_marginalmente_ao_cruzar_primeira_faixa() -> None:
    calculo = _calcular(producao="20000", anterior="70000")

    assert [item.producao for item in calculo.segmentos] == [
        Decimal("5000.00"),
        Decimal("15000.00"),
    ]
    assert [item.percentual for item in calculo.segmentos] == [Decimal("8"), Decimal("10")]
    assert calculo.comissao == Decimal("665.00")
    assert calculo.producao_posterior == Decimal("90000.00")


def test_rateia_uma_parcela_que_cruza_as_duas_faixas() -> None:
    calculo = _calcular(producao="120000", anterior="70000")

    assert [item.producao for item in calculo.segmentos] == [
        Decimal("5000.00"),
        Decimal("100000.00"),
        Decimal("15000.00"),
    ]
    assert calculo.comissao == Decimal("4243.75")


@pytest.mark.parametrize(
    ("tps", "percentual"),
    (("24.99", "2"), ("25", "4"), ("29.99", "4"), ("30", "6"), ("34.99", "6"), ("35", "8")),
)
def test_limites_exatos_de_tps(tps: str, percentual: str) -> None:
    calculo = _calcular(producao="10000", tps=tps)
    assert calculo.segmentos[0].percentual == Decimal(percentual)


def test_pagamento_parcial_avanca_somente_a_producao_proporcional() -> None:
    calculo = calcular_consultor_escalonado(
        valor_operacao=Decimal("100000"),
        comissao_empresa_total=Decimal("35000"),
        valor_recebido_elegivel=Decimal("17500"),
        tps=Decimal("35"),
        producao_anterior=Decimal("0"),
        faixas_producao=_producao(),
        faixas_tps=_tps(),
    )
    assert calculo.producao_reconhecida == Decimal("50000.00")
    assert calculo.comissao == Decimal("1400.00")
