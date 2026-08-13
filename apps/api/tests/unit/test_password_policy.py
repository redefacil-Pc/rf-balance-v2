"""Política de senha: comprimento acima de composição obrigatória."""

import pytest

from app.modules.identity.domain.errors import WeakPasswordError
from app.modules.identity.domain.policies import password_policy


def test_aceita_frase_longa_sem_simbolo() -> None:
    password_policy.validar("cavalo bateria grampo azul")


def test_rejeita_abaixo_do_minimo() -> None:
    with pytest.raises(WeakPasswordError):
        password_policy.validar("curta123")


def test_rejeita_acima_do_maximo() -> None:
    with pytest.raises(WeakPasswordError):
        password_policy.validar("a" * 129)


def test_rejeita_senha_previsivel_independente_de_caixa() -> None:
    with pytest.raises(WeakPasswordError):
        password_policy.validar("  RFBalance  ")
