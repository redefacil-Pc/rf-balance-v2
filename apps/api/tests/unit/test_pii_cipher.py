"""Cifragem de PII e hash de busca (ADR-0012)."""

import base64

import pytest

from app.platform.security.pii_cipher import PiiCipher, PiiCipherError, criar

CHAVE = base64.b64encode(b"0" * 32).decode("ascii")
PEPPER = "pepper-de-teste-com-tamanho-ok"


def _cipher() -> PiiCipher:
    return criar(CHAVE, PEPPER)


def test_ciclo_de_cifragem_preserva_o_valor() -> None:
    cipher = _cipher()

    assert cipher.decifrar(cipher.cifrar("52998224725")) == "52998224725"


def test_mesmo_valor_gera_cifras_diferentes() -> None:
    """Nonce aleatório: o cifrado não pode vazar repetição de valor."""
    cipher = _cipher()

    assert cipher.cifrar("52998224725") != cipher.cifrar("52998224725")


def test_hash_de_busca_e_deterministico() -> None:
    cipher = _cipher()

    assert cipher.hash_de_busca("52998224725") == cipher.hash_de_busca("52998224725")


def test_pepper_diferente_gera_hash_diferente() -> None:
    """É o que impede ataque de dicionário sobre CPF."""
    outro = criar(CHAVE, "outro-pepper-com-tamanho-ok")

    assert _cipher().hash_de_busca("52998224725") != outro.hash_de_busca("52998224725")


def test_cifra_adulterada_e_rejeitada() -> None:
    cipher = _cipher()
    cifrado = cipher.cifrar("52998224725")
    corrompido = cifrado[:-4] + ("AAAA" if not cifrado.endswith("AAAA") else "BBBB")

    with pytest.raises(PiiCipherError):
        cipher.decifrar(corrompido)


def test_versao_desconhecida_e_rejeitada() -> None:
    with pytest.raises(PiiCipherError):
        _cipher().decifrar("v9:AAAA")


def test_chave_de_tamanho_errado_e_rejeitada() -> None:
    with pytest.raises(PiiCipherError):
        criar(base64.b64encode(b"curta").decode("ascii"), PEPPER)
