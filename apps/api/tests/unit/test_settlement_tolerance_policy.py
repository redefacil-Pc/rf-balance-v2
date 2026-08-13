"""Tolerância de quitação observada no v1: -R$ 10,00 / +R$ 100,00 (seção 7.4)."""

from __future__ import annotations

import pytest

from app.modules.commercial.domain.policies.settlement_tolerance_policy import (
    ResultadoDeQuitacao,
    resolver,
    vigente,
)
from app.shared.domain.dinheiro import Dinheiro

ESPERADO = Dinheiro.de("1000.00")


@pytest.mark.parametrize(
    ("recebido", "resultado"),
    [
        ("0.00", ResultadoDeQuitacao.EM_ABERTO),
        ("989.99", ResultadoDeQuitacao.EM_ABERTO),
        # exatamente no limite de falta: ainda quita
        ("990.00", ResultadoDeQuitacao.QUITADA),
        ("1000.00", ResultadoDeQuitacao.QUITADA),
        # exatamente no limite de excedente: ainda quita
        ("1100.00", ResultadoDeQuitacao.QUITADA),
        ("1100.01", ResultadoDeQuitacao.SOBREPAGAMENTO),
    ],
)
def test_faixas_de_tolerancia(recebido: str, resultado: ResultadoDeQuitacao) -> None:
    classificacao = vigente().classificar(esperado=ESPERADO, recebido=Dinheiro.de(recebido))
    assert classificacao is resultado


def test_versao_desconhecida_nao_cai_na_vigente() -> None:
    # silenciar aqui reescreveria a história de um fechamento já feito
    with pytest.raises(ValueError):
        resolver("v99")


def test_v1_carrega_os_limites_observados() -> None:
    politica = resolver("v1")
    assert politica.falta_tolerada == Dinheiro.de("10.00")
    assert politica.excedente_tolerado == Dinheiro.de("100.00")
