"""Porta de persistência de usuário."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.modules.identity.domain.entities.user import User
from app.modules.identity.domain.value_objects.email_address import EmailAddress


class UserRepository(Protocol):
    async def buscar_por_email(self, email: EmailAddress) -> User | None:
        """Traz o usuário com papéis e permissões resolvidos em uma única consulta."""
        ...

    async def buscar_por_id(self, user_id: int) -> User | None: ...

    async def registrar_acesso(self, user_id: int, quando: datetime) -> None: ...
