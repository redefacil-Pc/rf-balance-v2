"""Semeadura das contas iniciais.

A estrutura de RBAC (permissões, papéis e a composição entre eles) **não** mora
aqui: é `rbac_sync`, porque é derivada do código e precisa ser reaplicada a cada
deploy. Aqui fica o que é dado — a conta que nasce uma vez e depois se gerencia
pela tela.

Idempotente: rodar duas vezes não duplica nem sobrescreve senha existente.
A senha de cada conta vem da variável de ambiente correspondente
(`SEED_ADMIN_PASSWORD`, `SEED_FINANCEIRO_PASSWORD`, ...); sem ela, o seed gera
uma senha aleatória e a imprime **uma única vez** — nenhuma senha padrão fica no
código.

Os perfis existem porque o fluxo de proposta depende da separação entre eles:
operação cadastra e envia, financeiro decide, administração cobre o resto.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.domain.permission_catalog import NOMES_DOS_PAPEIS
from app.modules.identity.infrastructure import rbac_sync
from app.modules.identity.infrastructure.hashing.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from app.modules.identity.infrastructure.models.role_model import RoleModel
from app.modules.identity.infrastructure.models.user_model import UserModel
from app.modules.identity.infrastructure.models.user_role_model import UserRoleModel

EMAIL_ADMIN_PADRAO = "admin@rfbalance.local"
EMAIL_FINANCEIRO_PADRAO = "financeiro@rfbalance.local"
EMAIL_OPERACIONAL_PADRAO = "operacional@rfbalance.local"
EMAIL_LIDERANCA_PADRAO = "lideranca@rfbalance.local"
EMAIL_CONSULTOR_PADRAO = "consultor@rfbalance.local"


@dataclass(frozen=True, slots=True)
class UsuarioInicial:
    """Uma conta do seed e o prefixo das variáveis que a configuram."""

    papel: str
    email_padrao: str
    nome_padrao: str
    prefixo: str
    #: conta que só nasce quando o operador define a senha explicitamente.
    #: Serve para perfil que existe no catálogo mas ainda não deve sair criado
    #: por padrão — criar por engano é mais caro que digitar uma variável.
    sob_demanda: bool = False

    @property
    def email(self) -> str:
        return os.getenv(f"SEED_{self.prefixo}_EMAIL", self.email_padrao).strip().lower()

    @property
    def nome(self) -> str:
        return os.getenv(f"SEED_{self.prefixo}_NAME", self.nome_padrao)

    @property
    def variavel_de_senha(self) -> str:
        return f"SEED_{self.prefixo}_PASSWORD"

    @property
    def deve_criar(self) -> bool:
        return not self.sob_demanda or self.variavel_de_senha in os.environ


USUARIOS_INICIAIS: tuple[UsuarioInicial, ...] = (
    UsuarioInicial("ADMIN", EMAIL_ADMIN_PADRAO, "Administrador", "ADMIN"),
    UsuarioInicial("FINANCEIRO", EMAIL_FINANCEIRO_PADRAO, "Financeiro", "FINANCEIRO"),
    UsuarioInicial("OPERACIONAL", EMAIL_OPERACIONAL_PADRAO, "Operacional", "OPERACIONAL"),
    UsuarioInicial(
        "LIDERANCA",
        EMAIL_LIDERANCA_PADRAO,
        "Liderança",
        "LIDERANCA",
        sob_demanda=True,
    ),
    # sob demanda porque conta de consultor sem colaborador vinculado não
    # enxerga nada — o escopo é por participação, e sem vínculo não há "meu"
    UsuarioInicial("CONSULTOR", EMAIL_CONSULTOR_PADRAO, "Consultor", "CONSULTOR", sob_demanda=True),
)


async def semear(session: AsyncSession) -> list[str]:
    """Sincroniza o RBAC e cria as contas iniciais.

    Retorna as mensagens do que aconteceu, para o operador ler no terminal.
    """
    relatorio = await rbac_sync.sincronizar(session)
    mensagens = relatorio.mensagens()

    papeis = {r.code: r for r in (await session.scalars(select(RoleModel))).all()}
    for usuario in USUARIOS_INICIAIS:
        if not usuario.deve_criar:
            mensagens.append(
                f"{NOMES_DOS_PAPEIS[usuario.papel]} não criado — "
                f"defina {usuario.variavel_de_senha} para criar"
            )
            continue
        await _semear_usuario(session, usuario, papeis, mensagens)

    return mensagens


async def _semear_usuario(
    session: AsyncSession,
    inicial: UsuarioInicial,
    papeis: dict[str, RoleModel],
    mensagens: list[str],
) -> None:
    email = inicial.email
    rotulo = NOMES_DOS_PAPEIS[inicial.papel]
    existente = await session.scalar(select(UserModel).where(UserModel.email == email))

    if existente is not None:
        mensagens.append(f"{rotulo} {email} já existe — senha preservada")
        return

    senha = os.getenv(inicial.variavel_de_senha) or secrets.token_urlsafe(16)
    gerada = inicial.variavel_de_senha not in os.environ

    usuario = UserModel(
        email=email,
        full_name=inicial.nome,
        password_hash=Argon2PasswordHasher().gerar(senha),
        is_active=True,
        must_change_password=gerada,
    )
    session.add(usuario)
    await session.flush()
    session.add(UserRoleModel(user_id=usuario.id, role_id=papeis[inicial.papel].id))

    mensagens.append(f"{rotulo} criado: {email}")
    if gerada:
        mensagens.append(
            f"senha gerada de {email} (anote agora, não será exibida de novo): {senha}"
        )
