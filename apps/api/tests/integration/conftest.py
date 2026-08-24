"""Infraestrutura dos testes de integração.

Roda contra MySQL e Redis reais, em banco separado (`rfbalance_test`). As
migrações são aplicadas pelo Alembic — nunca por `create_all`, para o teste
exercitar o mesmo schema que a produção recebe.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "mysql+asyncmy://rfbalance:rfbalance@db:3306/rfbalance_test"
)
TEST_MIGRATION_URL = os.getenv("TEST_MIGRATION_DATABASE_URL", TEST_DATABASE_URL)

# precisa acontecer antes de qualquer import que leia settings
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["MIGRATION_DATABASE_URL"] = TEST_MIGRATION_URL
os.environ["APP_ENV"] = "test"
os.environ.setdefault("SECRET_KEY", "chave-de-teste-com-mais-de-32-caracteres")
os.environ["COOKIE_SECURE"] = "true"
os.environ.setdefault("REDIS_URL", "redis://redis:6379/9")
os.environ.setdefault("LOGIN_MAX_ATTEMPTS", "5")
os.environ.setdefault("LOGIN_ATTEMPT_WINDOW", "900")

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.modules.identity.infrastructure.hashing.argon2_password_hasher import (  # noqa: E402
    Argon2PasswordHasher,
)
from app.platform.config.settings import get_settings  # noqa: E402
from app.platform.db.engine import criar_engine  # noqa: E402

#: Todas as tabelas mutáveis, das folhas para as raízes. Tabela nova entra aqui,
#: senão o estado vaza entre testes e a suíte passa a depender da ordem.
TABELAS_LIMPAS = (
    "data_integrity_checks",
    "stored_documents",
    "document_jobs",
    "commission_settlements",
    "commission_manual_entries",
    "commission_periods",
    "commission_entries",
    "commission_calculation_snapshots",
    "commission_rule_assignments",
    "commission_beneficiary_policies",
    "audit_events",
    "outbox_events",
    "login_attempts",
    "sessions",
    "legacy_import_issues",
    "legacy_import_runs",
    "proposal_attachments",
    "receipt_reversals",
    "receipts",
    "receiving_accounts",
    "proposals",
    "team_assignments",
    "collaborator_roles",
    "collaborator_payment_keys",
    "collaborators",
    "units",
    "companies",
    "user_roles",
    "role_permissions",
    "users",
    "roles",
    "permissions",
)

SENHA_DO_ADMIN = "senha-de-teste-longa-2026"


@pytest.fixture(scope="session", autouse=True)
def _migrar() -> None:
    from alembic import command
    from alembic.config import Config

    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")


@pytest.fixture(autouse=True)
async def _limpar_banco() -> AsyncIterator[None]:
    """Cada teste começa com o schema vazio: teste não herda estado de outro."""
    engine = criar_engine(get_settings().database)
    async with engine.begin() as conexao:
        await conexao.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for tabela in TABELAS_LIMPAS:
            await conexao.execute(text(f"TRUNCATE TABLE {tabela}"))
        await conexao.execute(text("DELETE FROM commission_rules WHERE rule_set_id <> 1"))
        await conexao.execute(text("DELETE FROM commission_rule_sets WHERE id <> 1"))
        await conexao.execute(text("DELETE FROM commission_strategy_configs WHERE id > 5"))
        await conexao.execute(
            text(
                "UPDATE commission_strategy_configs SET status='ACTIVE', valid_to=NULL, "
                "activated_by=NULL WHERE id <= 5"
            )
        )
        await conexao.execute(
            text(
                "UPDATE commission_rule_sets SET status='ACTIVE', valid_to=NULL, "
                "activated_by=NULL WHERE id=1"
            )
        )
        await conexao.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    await engine.dispose()

    yield


@pytest.fixture
async def app_em_teste() -> AsyncIterator[Any]:
    """A aplicação com o lifespan ativo, compartilhada pelos clientes do teste."""
    from asgi_lifespan import LifespanManager

    from app.main import criar_app

    app = criar_app()
    async with LifespanManager(app):
        yield app


def _cliente_de(app: Any) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app), base_url="https://testserver", follow_redirects=False
    )


@pytest.fixture
async def cliente(app_em_teste: Any) -> AsyncIterator[AsyncClient]:
    """Cliente HTTP com o lifespan da aplicação ativo."""
    async with _cliente_de(app_em_teste) as cliente:
        yield cliente


@pytest.fixture
def novo_cliente(app_em_teste: Any) -> Callable[[], AsyncClient]:
    """Fábrica de clientes adicionais no mesmo app.

    Cada cliente tem o seu próprio pote de cookies, que é o que permite manter
    duas sessões simultâneas — necessário para verificar que mexer no acesso de
    alguém derruba a sessão *daquela pessoa*, e não a de quem administra.
    """
    return lambda: _cliente_de(app_em_teste)


@pytest.fixture
async def admin_semeado(_limpar_banco: None) -> dict[str, str]:
    """Cria permissões, papéis e o administrador com senha conhecida."""
    from app.modules.identity.infrastructure import seed_identity
    from app.platform.db.session.session_factory import criar_fabrica_de_sessoes

    engine = criar_engine(get_settings().database)
    fabrica = criar_fabrica_de_sessoes(engine)
    try:
        async with fabrica() as session:
            os.environ["SEED_ADMIN_PASSWORD"] = SENHA_DO_ADMIN
            await seed_identity.semear(session)
            await session.commit()
    finally:
        await engine.dispose()

    return {"email": seed_identity.EMAIL_ADMIN_PADRAO, "senha": SENHA_DO_ADMIN}


@pytest.fixture
def hasher() -> Argon2PasswordHasher:
    return Argon2PasswordHasher()
