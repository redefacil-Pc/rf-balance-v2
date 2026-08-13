"""Dinheiro: normalização, arredondamento e aritmética."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.shared.domain.dinheiro import Dinheiro


def test_normaliza_para_duas_casas() -> None:
    assert Dinheiro.de("10").valor == Decimal("10.00")
    assert str(Dinheiro.de("1234.5")) == "1234.50"


def test_arredonda_half_up_e_nao_bankers() -> None:
    # o `round` do Python devolveria 0.12 aqui; o financeiro espera 0.13
    assert Dinheiro(Decimal("0.125")).valor == Decimal("0.13")
    assert Dinheiro(Decimal("0.135")).valor == Decimal("0.14")


def test_soma_e_subtracao_preservam_centavos() -> None:
    total = Dinheiro.de("0.10") + Dinheiro.de("0.20")
    assert total.valor == Decimal("0.30")
    assert (Dinheiro.de("100.00") - Dinheiro.de("100.01")).valor == Decimal("-0.01")


def test_comparacao_por_valor() -> None:
    assert Dinheiro.de("10.00") == Dinheiro.de("10.000")
    assert Dinheiro.de("9.99") < Dinheiro.de("10.00")


def test_zero_e_positivo() -> None:
    assert Dinheiro.zero().zerado
    assert not Dinheiro.zero().positivo
    assert Dinheiro.de("0.01").positivo


def test_recusa_entrada_invalida() -> None:
    with pytest.raises(ValueError):
        Dinheiro.de("dez reais")
