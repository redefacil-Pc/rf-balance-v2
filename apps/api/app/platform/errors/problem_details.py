"""Problem Details (RFC 7807) — formato único de erro da API."""

from __future__ import annotations

from dataclasses import dataclass, field

BASE_URI = "https://rfbalance/errors"


@dataclass(frozen=True, slots=True)
class FieldError:
    field: str
    message: str


@dataclass(frozen=True, slots=True)
class ProblemDetails:
    type: str
    title: str
    status: int
    detail: str
    instance: str
    correlation_id: str
    errors: list[FieldError] = field(default_factory=list)

    @classmethod
    def de_codigo(
        cls,
        *,
        code: str,
        title: str,
        status: int,
        detail: str,
        instance: str,
        correlation_id: str,
        errors: list[FieldError] | None = None,
    ) -> ProblemDetails:
        return cls(
            type=f"{BASE_URI}/{code}",
            title=title,
            status=status,
            detail=detail,
            instance=instance,
            correlation_id=correlation_id,
            errors=errors or [],
        )

    def para_dicionario(self) -> dict[str, object]:
        return {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "instance": self.instance,
            "correlation_id": self.correlation_id,
            "errors": [{"field": e.field, "message": e.message} for e in self.errors],
        }
