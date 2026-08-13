"""CPF e CNPJ: normalização, dígito verificador e mascaramento."""

import pytest

from app.shared.domain.documento import Documento, TipoDeDocumento


def test_normaliza_cpf_com_mascara() -> None:
    documento = Documento.normalizar("529.982.247-25")

    assert documento.digitos == "52998224725"
    assert documento.tipo is TipoDeDocumento.CPF


def test_normaliza_cnpj_com_mascara() -> None:
    documento = Documento.normalizar("11.222.333/0001-81")

    assert documento.digitos == "11222333000181"
    assert documento.tipo is TipoDeDocumento.CNPJ


@pytest.mark.parametrize("invalido", ["529.982.247-26", "11111111111", "123", "52998224725x9"])
def test_rejeita_cpf_invalido(invalido: str) -> None:
    with pytest.raises(ValueError):
        Documento.normalizar(invalido)


def test_rejeita_cnpj_com_digito_errado() -> None:
    with pytest.raises(ValueError):
        Documento.normalizar("11.222.333/0001-82")


def test_mascara_esconde_o_inicio_do_cpf() -> None:
    mascarado = Documento.normalizar("529.982.247-25").mascarado()

    assert mascarado == "***.***.247-25"
    assert "529" not in mascarado


def test_formatado_devolve_o_documento_completo() -> None:
    assert Documento.normalizar("52998224725").formatado() == "529.982.247-25"
    assert Documento.normalizar("11222333000181").formatado() == "11.222.333/0001-81"
