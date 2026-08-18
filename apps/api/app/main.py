"""Composição da aplicação. Nada de regra de negócio neste arquivo."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.audit.api.routes.audit_events import router as audit_events_router
from app.modules.commercial.api.routes.proposals import router as proposals_router
from app.modules.commissions.api.routes.beneficiary_policies import (
    router as beneficiary_policies_router,
)
from app.modules.commissions.api.routes.commission_explanations import (
    router as commission_explanations_router,
)
from app.modules.commissions.api.routes.commission_rules import router as commission_rules_router
from app.modules.commissions.api.routes.financial_report import (
    router as financial_report_router,
)
from app.modules.commissions.api.routes.periods import router as periods_router
from app.modules.commissions.api.routes.settlements import router as settlements_router
from app.modules.commissions.api.routes.strategy_configs import router as strategy_configs_router
from app.modules.identity.api.routes.auth import router as auth_router
from app.modules.identity.api.routes.users import router as users_router
from app.modules.identity.infrastructure.rbac_readiness import montar_check as check_de_rbac
from app.modules.organization.api.routes.collaborators import router as collaborators_router
from app.modules.organization.api.routes.companies import router as companies_router
from app.modules.receivables.api.routes.receipts import router as receipts_router
from app.modules.reporting.api.routes.dashboard import router as dashboard_router
from app.modules.teams.api.routes.assignments import router as assignments_router
from app.platform.cache.redis_client import criar_cliente as criar_redis
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes
from app.platform.errors.handlers import registrar_tratadores
from app.platform.http.correlation import CorrelationIdMiddleware
from app.platform.http.health_router import router as health_router
from app.platform.observability.logging import configurar_logging
from app.platform.observability.metrics import HttpMetricsMiddleware
from app.platform.observability.metrics import router as metrics_router
from app.platform.security import csrf
from app.platform.security import pii_cipher as pii
from app.platform.storage.object_storage import criar_cliente as criar_storage
from app.platform.time.clock import SystemClock

_logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.validar()  # fail-fast antes de aceitar tráfego

    engine = criar_engine(settings.database)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = criar_fabrica_de_sessoes(engine)
    # o readiness acusa RBAC defasado em vez de deixar a API negar acesso em
    # silêncio quando o catálogo anda e o banco não
    app.state.readiness_extras = (check_de_rbac(app.state.session_factory),)
    app.state.redis = criar_redis(settings.redis)
    app.state.storage = criar_storage(settings.storage)
    app.state.clock = SystemClock(settings.app.app_timezone)
    app.state.pii_cipher = pii.criar(settings.pii.chave, settings.pii.pepper)

    _logger.info("api_iniciada", environment=settings.app.app_env)
    try:
        yield
    finally:
        await app.state.redis.aclose()
        await engine.dispose()
        _logger.info("api_encerrada")


def criar_app() -> FastAPI:
    settings = get_settings()
    configurar_logging(settings.app.log_level, settings.app.app_env)

    app = FastAPI(
        title="RF Balance API",
        version="0.1.0",
        docs_url=None if settings.app.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.app.is_production else "/openapi.json",
        lifespan=lifespan,
        # CSRF em toda rota de método não seguro (ADR-0003), não só nas que
        # resolvem usuário
        dependencies=[Depends(csrf.guard)],
    )

    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(HttpMetricsMiddleware)
    if settings.app.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.app.cors_origins,  # allowlist exata
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Correlation-ID"],
            expose_headers=["X-Correlation-ID", "ETag"],
        )

    registrar_tratadores(app)
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(auth_router)
    app.include_router(audit_events_router)
    app.include_router(users_router)
    app.include_router(companies_router)
    app.include_router(collaborators_router)
    app.include_router(assignments_router)
    app.include_router(proposals_router)
    app.include_router(receipts_router)
    app.include_router(dashboard_router)
    app.include_router(commission_rules_router)
    app.include_router(commission_explanations_router)
    app.include_router(financial_report_router)
    app.include_router(beneficiary_policies_router)
    app.include_router(strategy_configs_router)
    app.include_router(settlements_router)
    app.include_router(periods_router)
    return app


app = criar_app()
