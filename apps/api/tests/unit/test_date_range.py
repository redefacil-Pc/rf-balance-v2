"""Intervalos fechados nas duas pontas (ADR-0013).

Erro de um dia na fronteira troca o beneficiário da comissão, por isso os casos
de fronteira são explícitos aqui.
"""

from datetime import date

import pytest

from app.shared.domain.date_range import DateRange


def test_rejeita_fim_antes_do_inicio() -> None:
    with pytest.raises(ValueError):
        DateRange(date(2026, 8, 10), date(2026, 8, 9))


def test_aceita_intervalo_de_um_unico_dia() -> None:
    intervalo = DateRange(date(2026, 8, 10), date(2026, 8, 10))

    assert intervalo.contem(date(2026, 8, 10))


def test_contem_as_duas_fronteiras() -> None:
    intervalo = DateRange(date(2026, 8, 1), date(2026, 8, 31))

    assert intervalo.contem(date(2026, 8, 1))
    assert intervalo.contem(date(2026, 8, 31))
    assert not intervalo.contem(date(2026, 7, 31))
    assert not intervalo.contem(date(2026, 9, 1))


def test_vigencia_aberta_contem_qualquer_data_futura() -> None:
    intervalo = DateRange(date(2026, 8, 1))

    assert intervalo.aberto
    assert intervalo.contem(date(2030, 1, 1))
    assert not intervalo.contem(date(2026, 7, 31))


def test_intervalos_adjacentes_nao_se_sobrepoem() -> None:
    anterior = DateRange(date(2026, 8, 1), date(2026, 8, 10))
    seguinte = DateRange(date(2026, 8, 11), date(2026, 8, 20))

    assert not anterior.sobrepoe(seguinte)
    assert not seguinte.sobrepoe(anterior)


def test_intervalos_que_compartilham_um_dia_se_sobrepoem() -> None:
    anterior = DateRange(date(2026, 8, 1), date(2026, 8, 11))
    seguinte = DateRange(date(2026, 8, 11), date(2026, 8, 20))

    assert anterior.sobrepoe(seguinte)


def test_vigencia_aberta_sobrepoe_tudo_que_vem_depois() -> None:
    aberta = DateRange(date(2026, 8, 1))
    futura = DateRange(date(2027, 1, 1), date(2027, 12, 31))

    assert aberta.sobrepoe(futura)
    assert futura.sobrepoe(aberta)


def test_transferencia_fecha_no_dia_anterior() -> None:
    vigente = DateRange(date(2026, 8, 1))

    encerrado = vigente.encerrar_em(date(2026, 8, 15))

    assert encerrado.fim == date(2026, 8, 14)
    assert not encerrado.sobrepoe(DateRange(date(2026, 8, 15)))


def test_transferencia_no_mesmo_dia_do_inicio_e_rejeitada() -> None:
    """Fechar em `inicio - 1` geraria intervalo negativo — não existe vínculo de
    duração zero."""
    vigente = DateRange(date(2026, 8, 15))

    with pytest.raises(ValueError):
        vigente.encerrar_em(date(2026, 8, 15))
