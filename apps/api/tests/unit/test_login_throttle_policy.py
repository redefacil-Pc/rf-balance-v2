"""Limite de tentativas de login (seção 13.1)."""

from app.modules.identity.domain.policies.login_throttle_policy import LoginThrottlePolicy

POLITICA = LoginThrottlePolicy(max_tentativas=5, janela_em_segundos=900)


def test_libera_abaixo_do_limite() -> None:
    assert not POLITICA.bloqueado(4)


def test_bloqueia_no_limite_exato() -> None:
    assert POLITICA.bloqueado(5)


def test_bloqueia_acima_do_limite() -> None:
    assert POLITICA.bloqueado(9)


def test_espera_corresponde_a_janela() -> None:
    assert POLITICA.espera_em_segundos() == 900
