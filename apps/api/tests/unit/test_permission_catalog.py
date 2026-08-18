"""Catálogo de permissões: coerência e separação de responsabilidades.

O fluxo de aprovação de proposta só faz sentido se quem cadastra não for quem
decide. Isso é uma regra de negócio, não detalhe de configuração — por isso ela
tem teste, e não só um comentário no catálogo.
"""

from __future__ import annotations

import pytest

from app.modules.identity.domain.permission_catalog import (
    NOMES_DOS_PAPEIS,
    PAPEIS,
    PERMISSOES,
)
from app.modules.identity.infrastructure.seed_identity import (
    USUARIOS_INICIAIS,
    UsuarioInicial,
)


def test_todo_papel_usa_apenas_permissoes_do_catalogo() -> None:
    for papel, permissoes in PAPEIS.items():
        desconhecidas = set(permissoes) - set(PERMISSOES)
        assert not desconhecidas, f"{papel} referencia permissão inexistente: {desconhecidas}"


def test_todo_papel_tem_nome_de_exibicao() -> None:
    assert set(PAPEIS) == set(NOMES_DOS_PAPEIS)


def test_todo_papel_lista_permissoes_sem_repetir() -> None:
    for papel, permissoes in PAPEIS.items():
        assert len(permissoes) == len(set(permissoes)), f"{papel} repete permissão"


def test_admin_cobre_o_catalogo_inteiro() -> None:
    assert set(PAPEIS["ADMIN"]) == set(PERMISSOES)


def test_operacional_cadastra_mas_nao_aprova() -> None:
    """A separação que dá sentido ao fluxo: quem sobe a proposta não decide."""
    operacional = set(PAPEIS["OPERACIONAL"])
    assert "proposals:write" in operacional
    assert "proposals:approve" not in operacional


def test_financeiro_aprova_mas_nao_cadastra() -> None:
    financeiro = set(PAPEIS["FINANCEIRO"])
    assert "proposals:approve" in financeiro
    assert "proposals:write" not in financeiro


def test_papeis_de_acesso_nao_replicam_funcoes_operacionais() -> None:
    assert set(PAPEIS) == {"ADMIN", "FINANCEIRO", "OPERACIONAL", "LIDERANCA", "CONSULTOR"}


def test_operacional_alcanca_as_telas_que_precisa() -> None:
    """Sem estas, o formulário de proposta abre quebrado: os selects de
    consultor, BKO e finalizador vêm de `collaborators`."""
    operacional = set(PAPEIS["OPERACIONAL"])
    assert {"proposals:read", "collaborators:read", "dashboard:read"} <= operacional


@pytest.mark.parametrize("inicial", USUARIOS_INICIAIS, ids=lambda u: u.papel)
def test_usuario_inicial_aponta_para_papel_existente(inicial: UsuarioInicial) -> None:
    assert inicial.papel in PAPEIS


def test_so_o_administrador_nasce_por_padrao() -> None:
    """Ambiente novo começa vazio: uma conta, e o resto se cadastra pela tela.

    O administrador é a única exceção porque sem ele ninguém entra para criar as
    demais. Financeiro e Operacional continuam existindo no seed, mas sob
    demanda — quem quer um ambiente pronto define a senha correspondente.

    Consequência conhecida e aceita: só com o administrador não se lança
    recebimento, porque a rota exige perfil Financeiro, ou Operacional com
    função FINALIZACAO vigente. Criar essas contas é o primeiro passo do fluxo
    real, não um contorno.
    """
    automaticos = {u.papel for u in USUARIOS_INICIAIS if not u.sob_demanda}
    assert automaticos == {"ADMIN"}


def test_seed_cobre_todo_papel_do_catalogo() -> None:
    """Papel novo sem entrada no seed é papel que ninguém consegue usar."""
    assert {u.papel for u in USUARIOS_INICIAIS} == set(PAPEIS)


def test_consultor_so_nasce_sob_demanda() -> None:
    """Trava de segurança, não de conveniência: sem escopo de dados, um
    consultor logado enxerga a carteira de todos. Ver o comentário do papel
    CONSULTOR no catálogo."""
    consultor = next(u for u in USUARIOS_INICIAIS if u.papel == "CONSULTOR")
    assert consultor.sob_demanda


def test_emails_dos_usuarios_iniciais_nao_colidem() -> None:
    emails = [u.email for u in USUARIOS_INICIAIS]
    assert len(emails) == len(set(emails))
