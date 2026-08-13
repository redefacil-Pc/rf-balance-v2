"""DTO do usuário autenticado.

`snake_case` por ADR-0015. Não expõe hash de senha nem dado de sessão.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.modules.identity.domain.entities.user import User


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    email: str
    full_name: str
    roles: list[str]
    permissions: list[str]
    must_change_password: bool

    @classmethod
    def de_usuario(cls, user: User) -> CurrentUserResponse:
        return cls(
            id=user.id,
            email=user.email.valor,
            full_name=user.full_name,
            roles=sorted(user.roles),
            permissions=sorted(user.permissions),
            must_change_password=user.must_change_password,
        )
