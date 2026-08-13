"""Fonte de tempo da aplicação.

Instantes são sempre UTC. A data operacional (`business_date`) é derivada do
fuso configurado e é um conceito distinto de `occurred_at`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo


class Clock(Protocol):
    def now(self) -> datetime: ...

    def business_date(self) -> date: ...


class SystemClock:
    __slots__ = ("_zone",)

    def __init__(self, timezone: str) -> None:
        self._zone = ZoneInfo(timezone)

    def now(self) -> datetime:
        return datetime.now(tz=UTC)

    def business_date(self) -> date:
        return self.now().astimezone(self._zone).date()


class FrozenClock:
    """Clock determinístico para testes."""

    __slots__ = ("_instant", "_zone")

    def __init__(self, instant: datetime, timezone: str = "America/Sao_Paulo") -> None:
        if instant.tzinfo is None:
            raise ValueError("instante precisa ter timezone")
        self._instant = instant.astimezone(UTC)
        self._zone = ZoneInfo(timezone)

    def now(self) -> datetime:
        return self._instant

    def business_date(self) -> date:
        return self._instant.astimezone(self._zone).date()
