"""Porta de registro e contagem de tentativas de login."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class LoginAttemptRepository(Protocol):
    async def registrar(
        self,
        *,
        email: str,
        ip_hash: str | None,
        sucesso: bool,
        motivo: str | None,
        quando: datetime,
    ) -> None: ...

    async def contar_falhas(self, *, email: str, ip_hash: str | None, desde: datetime) -> int:
        """Falhas na janela, considerando e-mail ou IP."""
        ...
