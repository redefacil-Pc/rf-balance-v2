"""Usuário: conta de acesso."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.identity.domain.value_objects.email_address import EmailAddress


@dataclass(slots=True)
class User:
    id: int
    email: EmailAddress
    full_name: str
    password_hash: str
    is_active: bool
    must_change_password: bool = False
    permissions: frozenset[str] = field(default_factory=frozenset)
    roles: frozenset[str] = field(default_factory=frozenset)

    def pode(self, permissao: str) -> bool:
        return permissao in self.permissions
