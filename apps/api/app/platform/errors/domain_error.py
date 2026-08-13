"""Erro de domínio: a única exceção que a API traduz em Problem Details de negócio."""

from __future__ import annotations


class DomainError(Exception):
    """Violação de regra de negócio.

    `code` alimenta o campo `type` do Problem Details e é contrato público —
    mudança de código é mudança de API.
    """

    status = 422
    code = "domain-error"
    title = "Regra de negócio violada"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class PeriodClosedError(DomainError):
    status = 409
    code = "period-closed"
    title = "Período fechado"


class ConcurrencyConflictError(DomainError):
    status = 409
    code = "concurrency-conflict"
    title = "Conflito de concorrência"


class PermissionDeniedError(DomainError):
    status = 403
    code = "permission-denied"
    title = "Permissão negada"
