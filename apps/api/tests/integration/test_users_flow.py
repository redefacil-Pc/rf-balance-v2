"""Administração de usuários, ponta a ponta.

Cobre o que dá errado na prática: e-mail repetido, papel inexistente, conta sem
papel, administrador se trancando do lado de fora, e — o mais silencioso de
todos — mudança de acesso que não vale porque a sessão em curso está em cache.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient, Response

from app.platform.config.security import CSRF_COOKIE, CSRF_HEADER

pytestmark = pytest.mark.integration


class Api:
    def __init__(self, cliente: AsyncClient) -> None:
        self._cliente = cliente

    @property
    def _csrf(self) -> dict[str, str]:
        return {CSRF_HEADER: self._cliente.cookies[CSRF_COOKIE]}

    async def post(self, caminho: str, corpo: dict[str, Any] | None = None) -> Response:
        return await self._cliente.post(caminho, json=corpo or {}, headers=self._csrf)

    async def put(self, caminho: str, corpo: dict[str, Any]) -> Response:
        return await self._cliente.put(caminho, json=corpo, headers=self._csrf)

    async def get(self, caminho: str, **params: Any) -> Response:
        return await self._cliente.get(caminho, params=params or None)


@pytest.fixture
async def api(cliente: AsyncClient, admin_semeado: dict[str, str]) -> Api:
    await cliente.post(
        "/api/v1/auth/login",
        json={"email": admin_semeado["email"], "password": admin_semeado["senha"]},
    )
    return Api(cliente)


async def _criar(
    api: Api,
    *,
    email: str = "novo@rfbalance.local",
    nome: str = "Pessoa Nova",
    papeis: list[str] | None = None,
) -> dict[str, Any]:
    resposta = await api.post(
        "/api/v1/users",
        {"email": email, "full_name": nome, "roles": papeis or ["OPERACIONAL"]},
    )
    assert resposta.status_code == 201, resposta.text
    corpo: dict[str, Any] = resposta.json()
    return corpo


# ---------- criação ----------


async def test_criacao_devolve_senha_provisoria_e_exige_troca(api: Api) -> None:
    criado = await _criar(api)

    assert criado["temporary_password"]
    assert criado["roles"] == ["OPERACIONAL"]

    detalhe = (await api.get(f"/api/v1/users/{criado['id']}")).json()
    assert detalhe["must_change_password"] is True
    assert detalhe["is_active"] is True
    # hash de senha não escapa por DTO nenhum
    assert "password_hash" not in detalhe


async def test_criacao_conjunta_vincula_funcao_e_torna_usuario_elegivel(api: Api) -> None:
    empresa = await api.post(
        "/api/v1/companies",
        {
            "legal_name": "Empresa dos Usuários LTDA",
            "trade_name": "Empresa dos Usuários",
            "document": "04.252.011/0001-10",
        },
    )
    assert empresa.status_code == 201, empresa.text

    resposta = await api.post(
        "/api/v1/users",
        {
            "email": "consultora-vinculada@rfbalance.local",
            "full_name": "Consultora Vinculada",
            "roles": ["CONSULTOR"],
            "collaborator": {
                "company_id": empresa.json()["id"],
                "unit_id": None,
                "document": "529.982.247-25",
                "tax_regime": "MEI",
                "function": "CONSULTOR_MEI_ESCALONADO",
                "valid_from": "2026-01-01",
            },
        },
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["collaborator_id"] is not None

    elegiveis = await api.get(
        "/api/v1/collaborators",
        role="CONSULTOR_MEI_ESCALONADO",
        only_active=True,
        linked_user_only=True,
    )
    assert [item["full_name"] for item in elegiveis.json()["items"]] == ["Consultora Vinculada"]


async def test_falha_no_colaborador_desfaz_criacao_do_usuario(api: Api) -> None:
    resposta = await api.post(
        "/api/v1/users",
        {
            "email": "nao-pode-sobrar@rfbalance.local",
            "full_name": "Não Pode Sobrar",
            "roles": ["OPERACIONAL"],
            "collaborator": {
                "company_id": 999999,
                "unit_id": None,
                "document": "529.982.247-25",
                "tax_regime": "MEI",
                "function": "CONSULTOR",
                "valid_from": "2026-01-01",
            },
        },
    )
    assert resposta.status_code == 404

    usuarios = await api.get("/api/v1/users", search="Não Pode Sobrar")
    assert usuarios.json()["items"] == []


async def test_conta_sem_colaborador_e_valida(api: Api) -> None:
    """Administração e financeiro não são colaboradores comissionados. Exigir
    CPF e função dessas contas obrigaria a inventar dado, e dado inventado suja
    o cálculo de comissão depois."""
    criado = await _criar(api, email="admin2@rfbalance.local", papeis=["ADMIN"])

    assert criado["collaborator_id"] is None
    detalhe = (await api.get(f"/api/v1/users/{criado['id']}")).json()
    assert detalhe["roles"] == ["ADMIN"]


async def test_listagem_filtra_contas_ainda_vinculaveis(api: Api) -> None:
    """É a lista que a criação de colaborador oferece: só quem ainda não tem
    cadastro operacional."""
    sem_colaborador = await _criar(api, email="sozinho@rfbalance.local", papeis=["ADMIN"])

    disponiveis = await api.get("/api/v1/users", has_collaborator=False)
    ids = [u["id"] for u in disponiveis.json()["items"]]

    assert sem_colaborador["id"] in ids
    assert all(u["collaborator_id"] is None for u in disponiveis.json()["items"])


async def test_email_repetido_e_rejeitado(api: Api) -> None:
    await _criar(api, email="repetido@rfbalance.local")

    repetido = await api.post(
        "/api/v1/users",
        {"email": "repetido@rfbalance.local", "full_name": "Outra", "roles": ["OPERACIONAL"]},
    )

    assert repetido.status_code == 409
    assert repetido.json()["type"].endswith("email-ja-cadastrado")


async def test_email_normalizado_impede_duplicata_por_caixa(api: Api) -> None:
    await _criar(api, email="Caixa@RFBalance.local")

    igual = await api.post(
        "/api/v1/users",
        {"email": "caixa@rfbalance.local", "full_name": "Outra", "roles": ["OPERACIONAL"]},
    )

    assert igual.status_code == 409


async def test_edicao_administrativa_de_usuario_e_atomica(api: Api) -> None:
    criado = await _criar(
        api, email="atomico@rfbalance.local", papeis=["OPERACIONAL"]
    )
    user_id = criado["id"]

    invalido = await api.put(
        f"/api/v1/users/{user_id}",
        {
            "email": "alterado@rfbalance.local",
            "full_name": "Nome não pode persistir",
            "roles": ["PAPEL_INEXISTENTE"],
            "is_active": False,
        },
    )
    assert invalido.status_code == 422
    preservado = (await api.get(f"/api/v1/users/{user_id}")).json()
    assert preservado["email"] == "atomico@rfbalance.local"
    assert preservado["roles"] == ["OPERACIONAL"]
    assert preservado["is_active"] is True

    alterado = await api.put(
        f"/api/v1/users/{user_id}",
        {
            "email": "alterado@rfbalance.local",
            "full_name": "Nome Alterado",
            "roles": ["FINANCEIRO"],
            "is_active": False,
        },
    )
    assert alterado.status_code == 200, alterado.text
    assert alterado.json()["roles"] == ["FINANCEIRO"]
    assert alterado.json()["is_active"] is False


async def test_papel_inexistente_e_rejeitado(api: Api) -> None:
    resposta = await api.post(
        "/api/v1/users",
        {"email": "x@rfbalance.local", "full_name": "Pessoa", "roles": ["NAO_EXISTE"]},
    )

    assert resposta.status_code == 422
    assert resposta.json()["type"].endswith("papel-inexistente")


async def test_conta_sem_papel_nao_passa_do_schema(api: Api) -> None:
    resposta = await api.post(
        "/api/v1/users", {"email": "y@rfbalance.local", "full_name": "Pessoa", "roles": []}
    )
    assert resposta.status_code == 422


async def test_email_invalido_e_rejeitado(api: Api) -> None:
    resposta = await api.post(
        "/api/v1/users", {"email": "sem-arroba", "full_name": "Pessoa", "roles": ["OPERACIONAL"]}
    )
    assert resposta.status_code == 422


# ---------- consulta ----------


async def test_listagem_filtra_por_papel_e_busca(api: Api) -> None:
    await _criar(api, email="a@rfbalance.local", nome="Ana Financeira", papeis=["FINANCEIRO"])
    await _criar(api, email="b@rfbalance.local", nome="Bruno Operacional", papeis=["OPERACIONAL"])

    por_papel = await api.get("/api/v1/users", role="FINANCEIRO")
    nomes = [u["full_name"] for u in por_papel.json()["items"]]
    assert "Ana Financeira" in nomes
    assert "Bruno Operacional" not in nomes

    por_busca = await api.get("/api/v1/users", search="Bruno")
    assert [u["full_name"] for u in por_busca.json()["items"]] == ["Bruno Operacional"]


async def test_catalogo_de_papeis_vem_do_codigo(api: Api) -> None:
    resposta = await api.get("/api/v1/users/roles")

    assert resposta.status_code == 200
    codigos = {p["code"] for p in resposta.json()}
    assert {
        "ADMIN",
        "CONSULTOR",
        "FINANCEIRO",
        "OPERACIONAL",
        "LIDERANCA",
    } == codigos


async def test_usuario_inexistente_devolve_404(api: Api) -> None:
    assert (await api.get("/api/v1/users/999999")).status_code == 404


# ---------- alteração ----------


async def test_alteracao_de_cadastro(api: Api) -> None:
    criado = await _criar(api, email="antes@rfbalance.local", nome="Nome Antigo")

    alterado = await api.put(
        f"/api/v1/users/{criado['id']}",
        {"email": "depois@rfbalance.local", "full_name": "Nome Novo"},
    )

    assert alterado.status_code == 200, alterado.text
    assert alterado.json()["email"] == "depois@rfbalance.local"
    assert alterado.json()["full_name"] == "Nome Novo"


async def test_papeis_sao_substituidos_e_nao_somados(api: Api) -> None:
    criado = await _criar(api, papeis=["OPERACIONAL"])

    trocado = await api.put(
        f"/api/v1/users/{criado['id']}/roles", {"roles": ["OPERACIONAL", "LIDERANCA"]}
    )

    assert trocado.status_code == 200, trocado.text
    assert sorted(trocado.json()["roles"]) == ["LIDERANCA", "OPERACIONAL"]


async def test_desativacao_e_reativacao(api: Api) -> None:
    criado = await _criar(api)

    desativado = await api.put(f"/api/v1/users/{criado['id']}/status", {"is_active": False})
    assert desativado.status_code == 200
    assert desativado.json()["is_active"] is False

    reativado = await api.put(f"/api/v1/users/{criado['id']}/status", {"is_active": True})
    assert reativado.json()["is_active"] is True


async def test_reset_de_senha_gera_nova_provisoria(api: Api) -> None:
    criado = await _criar(api)

    reset = await api.post(f"/api/v1/users/{criado['id']}/password-reset")

    assert reset.status_code == 200, reset.text
    assert reset.json()["temporary_password"] != criado["temporary_password"]
    detalhe = (await api.get(f"/api/v1/users/{criado['id']}")).json()
    assert detalhe["must_change_password"] is True


async def test_senha_definida_pelo_administrador_vale_no_login(
    api: Api, novo_cliente: Callable[[], AsyncClient]
) -> None:
    """O que importa de verdade: a senha escolhida autentica."""
    criado = await _criar(api, email="escolhida@rfbalance.local")

    definida = await api.post(
        f"/api/v1/users/{criado['id']}/password-reset",
        {"password": "SenhaEscolhida2026", "require_change": False},
    )

    assert definida.status_code == 200, definida.text
    # não ecoa o segredo de volta: quem definiu já o conhece
    assert definida.json()["temporary_password"] is None
    assert definida.json()["must_change_password"] is False

    async with novo_cliente() as outro:
        entrou = await outro.post(
            "/api/v1/auth/login",
            json={"email": "escolhida@rfbalance.local", "password": "SenhaEscolhida2026"},
        )
        assert entrou.status_code == 200, entrou.text
        assert entrou.json()["must_change_password"] is False


async def test_senha_definida_pode_exigir_troca(api: Api) -> None:
    criado = await _criar(api, email="comtroca@rfbalance.local")

    definida = await api.post(
        f"/api/v1/users/{criado['id']}/password-reset",
        {"password": "OutraSenhaLonga2026", "require_change": True},
    )

    assert definida.status_code == 200, definida.text
    assert (await api.get(f"/api/v1/users/{criado['id']}")).json()["must_change_password"] is True


async def test_senha_fraca_e_recusada(api: Api) -> None:
    """Quem administra não instala senha que o próprio sistema recusaria."""
    criado = await _criar(api, email="fraca@rfbalance.local")

    curta = await api.post(f"/api/v1/users/{criado['id']}/password-reset", {"password": "curta"})

    assert curta.status_code == 422
    assert curta.json()["type"].endswith("weak-password")


async def test_reset_sem_corpo_continua_gerando(api: Api) -> None:
    """Compatibilidade: o corpo é opcional e a ausência gera, como antes."""
    criado = await _criar(api, email="semcorpo@rfbalance.local")

    reset = await api.post(f"/api/v1/users/{criado['id']}/password-reset")

    assert reset.json()["temporary_password"]
    assert reset.json()["must_change_password"] is True


# ---------- travas contra ficar sem administrador ----------


async def test_administrador_nao_desativa_a_propria_conta(
    api: Api, admin_semeado: dict[str, str]
) -> None:
    eu = (await api.get("/api/v1/auth/me")).json()

    resposta = await api.put(f"/api/v1/users/{eu['id']}/status", {"is_active": False})

    assert resposta.status_code == 409
    assert resposta.json()["type"].endswith("auto-alteracao-proibida")


async def test_administrador_nao_altera_os_proprios_papeis(api: Api) -> None:
    eu = (await api.get("/api/v1/auth/me")).json()

    resposta = await api.put(f"/api/v1/users/{eu['id']}/roles", {"roles": ["CONSULTOR"]})

    assert resposta.status_code == 409
    assert resposta.json()["type"].endswith("auto-alteracao-proibida")


# ---------- efeito imediato da mudança de acesso ----------


async def test_desativacao_derruba_a_sessao_em_curso(
    novo_cliente: Callable[[], AsyncClient], api: Api
) -> None:
    """O caso silencioso: sem invalidar o cache, a conta desativada continuaria
    trabalhando até o TTL vencer."""
    criado = await _criar(api, email="vitima@rfbalance.local")
    senha = criado["temporary_password"]

    async with novo_cliente() as outro:
        entrou = await outro.post(
            "/api/v1/auth/login", json={"email": "vitima@rfbalance.local", "password": senha}
        )
        assert entrou.status_code == 200, entrou.text
        # a sessão está viva e em cache
        assert (await outro.get("/api/v1/auth/me")).status_code == 200

        await api.put(f"/api/v1/users/{criado['id']}/status", {"is_active": False})

        depois = await outro.get("/api/v1/auth/me")
        assert depois.status_code == 401


async def test_troca_de_papeis_derruba_a_sessao_em_curso(
    novo_cliente: Callable[[], AsyncClient], api: Api
) -> None:
    criado = await _criar(api, email="trocado@rfbalance.local", papeis=["FINANCEIRO"])
    senha = criado["temporary_password"]

    async with novo_cliente() as outro:
        await outro.post(
            "/api/v1/auth/login", json={"email": "trocado@rfbalance.local", "password": senha}
        )
        assert (await outro.get("/api/v1/auth/me")).status_code == 200

        await api.put(f"/api/v1/users/{criado['id']}/roles", {"roles": ["CONSULTOR"]})

        # a sessão antiga carregava as permissões antigas: tem de cair
        assert (await outro.get("/api/v1/auth/me")).status_code == 401


# ---------- autorização ----------


async def test_sem_users_write_nao_administra(
    novo_cliente: Callable[[], AsyncClient], api: Api
) -> None:
    criado = await _criar(api, email="semperm@rfbalance.local", papeis=["OPERACIONAL"])
    senha = criado["temporary_password"]

    async with novo_cliente() as outro:
        await outro.post(
            "/api/v1/auth/login", json={"email": "semperm@rfbalance.local", "password": senha}
        )
        csrf = {CSRF_HEADER: outro.cookies[CSRF_COOKIE]}

        listagem = await outro.get("/api/v1/users")
        criacao = await outro.post(
            "/api/v1/users",
            json={"email": "z@rfbalance.local", "full_name": "Z", "roles": ["CONSULTOR"]},
            headers=csrf,
        )

    assert listagem.status_code == 403
    assert criacao.status_code == 403
