from decimal import Decimal

from app.modules.commissions.domain.group_commissions import (
    comissao_finalizador,
    comissao_lider_comercial,
    comissao_lider_finalizacao,
    comissao_progressiva,
)


def test_lider_comercial_respeita_tps_e_regime() -> None:
    config = {"mei_min_tps": "25", "mei_percentage": "3", "clt_percentage": "0"}
    assert comissao_lider_comercial(
        base_recebida=Decimal("12000"), tps=Decimal("30"), regime="MEI", configuracao=config
    ) == (Decimal("3"), Decimal("360.00"))
    assert comissao_lider_comercial(
        base_recebida=Decimal("12000"), tps=Decimal("24.99"), regime="MEI", configuracao=config
    )[1] == Decimal("0.00")


def test_lider_mei_geral_e_progressivo() -> None:
    total, segmentos = comissao_progressiva(
        Decimal("600000"),
        percentual_base=Decimal("35"),
        faixas=[
            {"min": "0", "max": "500000", "percentage": "1.2"},
            {"min": "500000", "max": "1000000", "percentage": "1"},
        ],
    )
    assert total == Decimal("2450.00")
    assert [item.base for item in segmentos] == [Decimal("175000.00"), Decimal("35000.00")]


def test_finalizacao_no_limite_e_excedente() -> None:
    config = {"threshold_amount": "70000", "fixed_amount": "500", "excess_percentage": "0.45"}
    assert comissao_finalizador(Decimal("69999.99"), config) == Decimal("0.00")
    assert comissao_finalizador(Decimal("70000"), config) == Decimal("500.00")
    assert comissao_finalizador(Decimal("80000"), config) == Decimal("545.00")


def test_lider_finalizacao() -> None:
    percentual, valor = comissao_lider_finalizacao(
        Decimal("80000"),
        regime="CLT",
        configuracao={"mei_percentage": "0.9", "clt_percentage": "0.9"},
    )
    assert percentual == Decimal("0.9")
    assert valor == Decimal("720.00")
