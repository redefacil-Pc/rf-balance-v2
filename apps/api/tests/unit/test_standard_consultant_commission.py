from decimal import Decimal

import pytest

from app.modules.commissions.domain.standard_consultant import (
    ConfiguracaoDeComissaoInvalidaError,
    FaixaConsultorPadrao,
    calcular_consultor_padrao,
    validar_faixas,
)


def _faixas(regime: str = "MEI") -> list[FaixaConsultorPadrao]:
    return [
        FaixaConsultorPadrao(1, regime, Decimal("0"), Decimal("25"), Decimal("6")),
        FaixaConsultorPadrao(2, regime, Decimal("25"), Decimal("30"), Decimal("8")),
        FaixaConsultorPadrao(3, regime, Decimal("30"), Decimal("35"), Decimal("10")),
        FaixaConsultorPadrao(4, regime, Decimal("35"), None, Decimal("12")),
    ]


@pytest.mark.parametrize(
    ("tps", "percentual"),
    [
        ("24.99", "6"),
        ("25", "8"),
        ("29.99", "8"),
        ("30", "10"),
        ("34.99", "10"),
        ("35", "12"),
        ("100", "12"),
    ],
)
def test_limites_exatos_de_tps(tps: str, percentual: str) -> None:
    calculo = calcular_consultor_padrao(
        valor_operacao=Decimal("100000"),
        comissao_empresa=Decimal("35000"),
        tps=Decimal(tps),
        valor_recebido_elegivel=Decimal("35000"),
        regime="MEI",
        faixas=_faixas(),
    )
    assert calculo.percentual == Decimal(percentual)


def test_pagamento_parcial_libera_comissao_e_producao_proporcionais() -> None:
    calculo = calcular_consultor_padrao(
        valor_operacao=Decimal("10000"),
        comissao_empresa=Decimal("3500"),
        tps=Decimal("35"),
        valor_recebido_elegivel=Decimal("1750"),
        regime="MEI",
        faixas=_faixas(),
    )
    assert calculo.producao_reconhecida == Decimal("5000.00")
    assert calculo.valor == Decimal("210.00")


def test_sobrepagamento_nao_comissiona_acima_de_cem_por_cento() -> None:
    calculo = calcular_consultor_padrao(
        valor_operacao=Decimal("10000"),
        comissao_empresa=Decimal("3500"),
        tps=Decimal("35"),
        valor_recebido_elegivel=Decimal("3600"),
        regime="MEI",
        faixas=_faixas(),
    )
    assert calculo.base_elegivel == Decimal("3500.00")
    assert calculo.producao_reconhecida == Decimal("10000.00")
    assert calculo.valor == Decimal("420.00")


def test_configuracao_com_lacuna_e_rejeitada() -> None:
    faixas = _faixas()
    faixas[1] = FaixaConsultorPadrao(2, "MEI", Decimal("26"), Decimal("30"), Decimal("8"))
    with pytest.raises(ConfiguracaoDeComissaoInvalidaError, match="lacuna ou sobreposição"):
        validar_faixas(faixas, "MEI")
