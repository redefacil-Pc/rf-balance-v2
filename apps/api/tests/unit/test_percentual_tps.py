"""TPS: limites e cálculo da comissão da empresa (seção 7.4)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.commercial.domain.value_objects.percentual_tps import PercentualTps
from app.shared.domain.dinheiro import Dinheiro


def test_aceita_os_extremos_do_intervalo() -> None:
    assert PercentualTps.de("0").valor == Decimal("0.000000")
    assert PercentualTps.de("100").valor == Decimal("100.000000")


@pytest.mark.parametrize("invalido", ["-0.01", "100.01", "200"])
def test_recusa_fora_de_zero_a_cem(invalido: str) -> None:
    with pytest.raises(ValueError):
        PercentualTps.de(invalido)


def test_comissao_da_empresa() -> None:
    tps = PercentualTps.de("12.5")
    assert tps.aplicar_sobre(Dinheiro.de("1000.00")) == Dinheiro.de("125.00")


def test_arredonda_uma_vez_no_fim_da_conta() -> None:
    # 3333.33 * 3.333333% = 111.1110... — arredondar antes daria outro centavo
    comissao = PercentualTps.de("3.333333").aplicar_sobre(Dinheiro.de("3333.33"))
    assert comissao == Dinheiro.de("111.11")


def test_tps_zero_nao_gera_comissao() -> None:
    assert PercentualTps.de("0").aplicar_sobre(Dinheiro.de("5000.00")).zerado
