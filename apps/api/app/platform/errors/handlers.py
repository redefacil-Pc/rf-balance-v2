"""Tradução de exceções em respostas `application/problem+json`."""

from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.platform.errors.domain_error import DomainError
from app.platform.errors.problem_details import FieldError, ProblemDetails

CONTENT_TYPE = "application/problem+json"
_logger = structlog.get_logger(__name__)


def _correlation_id(request: Request) -> str:
    return str(getattr(request.state, "correlation_id", ""))


def _resposta(problem: ProblemDetails) -> JSONResponse:
    return JSONResponse(
        status_code=problem.status,
        content=problem.para_dicionario(),
        media_type=CONTENT_TYPE,
    )


async def tratar_erro_de_dominio(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    return _resposta(
        ProblemDetails.de_codigo(
            code=exc.code,
            title=exc.title,
            status=exc.status,
            detail=exc.detail,
            instance=request.url.path,
            correlation_id=_correlation_id(request),
        )
    )


async def tratar_erro_de_validacao(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    erros = [
        FieldError(field=".".join(str(p) for p in erro["loc"][1:]), message=erro["msg"])
        for erro in exc.errors()
    ]
    return _resposta(
        ProblemDetails.de_codigo(
            code="validation-error",
            title="Requisição inválida",
            status=422,
            detail="Um ou mais campos são inválidos.",
            instance=request.url.path,
            correlation_id=_correlation_id(request),
            errors=erros,
        )
    )


async def tratar_erro_http(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    return _resposta(
        ProblemDetails.de_codigo(
            code="http-error",
            title=exc.detail if isinstance(exc.detail, str) else "Erro",
            status=exc.status_code,
            detail=str(exc.detail),
            instance=request.url.path,
            correlation_id=_correlation_id(request),
        )
    )


async def tratar_erro_inesperado(request: Request, exc: Exception) -> JSONResponse:
    """Nunca vaza mensagem interna: o detalhe vai para o log, não para o cliente."""
    _logger.exception("erro_inesperado", route=request.url.path, error=str(exc))
    return _resposta(
        ProblemDetails.de_codigo(
            code="internal-error",
            title="Erro interno",
            status=500,
            detail="Erro inesperado. Consulte o correlation_id no suporte.",
            instance=request.url.path,
            correlation_id=_correlation_id(request),
        )
    )


def registrar_tratadores(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, tratar_erro_de_dominio)
    app.add_exception_handler(RequestValidationError, tratar_erro_de_validacao)
    app.add_exception_handler(HTTPException, tratar_erro_http)
    app.add_exception_handler(Exception, tratar_erro_inesperado)
