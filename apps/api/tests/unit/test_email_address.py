"""E-mail é normalizado uma vez, na construção."""

import pytest

from app.modules.identity.domain.value_objects.email_address import EmailAddress


def test_normaliza_caixa_e_espacos() -> None:
    assert EmailAddress.normalizar("  Admin@RFBalance.Local  ").valor == "admin@rfbalance.local"


@pytest.mark.parametrize(
    "bruto", ["sem-arroba", "sem@dominio", "@sem-local.com", "com espaco@x.com"]
)
def test_rejeita_formato_invalido(bruto: str) -> None:
    with pytest.raises(ValueError):
        EmailAddress.normalizar(bruto)


def test_rejeita_tamanho_acima_do_limite() -> None:
    with pytest.raises(ValueError):
        EmailAddress.normalizar("a" * 320 + "@empresa.com")


def test_iguais_quando_normalizam_para_o_mesmo_valor() -> None:
    assert EmailAddress.normalizar("Joao@Empresa.com") == EmailAddress.normalizar(
        "joao@empresa.com"
    )
