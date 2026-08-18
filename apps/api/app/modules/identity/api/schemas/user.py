"""DTOs de usuário (`snake_case`, ADR-0015).

Senha não entra em nenhum request: quem administra não escolhe a senha de
ninguém. A criação e o reset devolvem uma provisória, exibida uma única vez, e a
conta fica com `must_change_password`.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.organization.domain.value_objects.papel_de_colaborador import (
    PapelDeColaborador,
    RegimeTributario,
)


class UserCollaboratorRequest(BaseModel):
    """Cadastro operacional criado junto da conta, quando a pessoa é as duas coisas.

    A função aqui é o que a pessoa **é** no negócio (consultor, BKO,
    finalização), distinta do perfil de acesso em `roles`, que é o que ela
    **pode fazer**. Uma função só na criação; acumular outras é pelas rotas de
    função do colaborador, que respeitam vigência.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    company_id: int
    unit_id: int | None = None
    document: str = Field(min_length=11, max_length=20)
    tax_regime: RegimeTributario
    function: PapelDeColaborador
    valid_from: date


class UserRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    email: str = Field(min_length=5, max_length=320)
    full_name: str = Field(min_length=3, max_length=200)
    #: ao menos um: conta sem papel loga e não enxerga nada
    roles: list[str] = Field(min_length=1)
    #: nulo para quem só usa o sistema. Administração e financeiro não são
    #: necessariamente colaboradores comissionados, e exigir CPF e função deles
    #: obrigaria a inventar dado que suja o cálculo de comissão depois.
    collaborator: UserCollaboratorRequest | None = None


class UpdateUserRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    email: str = Field(min_length=5, max_length=320)
    full_name: str = Field(min_length=3, max_length=200)
    roles: list[str] | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class SetRolesRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    #: conjunto final, não incremento
    roles: list[str] = Field(min_length=1)


class SetStatusRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    is_active: bool


class UserResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    email: str
    full_name: str
    is_active: bool
    must_change_password: bool
    roles: list[str]
    last_login_at: datetime | None
    #: nulo quando a pessoa só usa o sistema, sem cadastro operacional
    collaborator_id: int | None


class UserPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[UserResponse]
    next_cursor: str | None


class UserCreatedResponse(BaseModel):
    """A senha provisória aparece **uma vez**. Não há endpoint que a recupere."""

    model_config = ConfigDict(frozen=True)

    id: int
    email: str
    full_name: str
    roles: list[str]
    temporary_password: str
    collaborator_id: int | None = None


class PasswordResetRequest(BaseModel):
    """Corpo opcional: sem ele, o sistema gera a senha."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: nulo gera uma provisória. Preenchida, passa pela política de senha —
    #: o limite mínimo é validado no domínio, não aqui, para a regra morar num
    #: lugar só
    password: str | None = Field(default=None, max_length=128)
    #: quem define a senha passa a conhecê-la; por isso a troca no próximo
    #: acesso é o padrão
    require_change: bool = True


class PasswordResetResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    email: str
    #: só vem preenchida quando o sistema gerou. Senha escolhida por quem
    #: administra não volta no corpo: quem a definiu já a conhece.
    temporary_password: str | None
    must_change_password: bool


class RoleResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    name: str
    permissions: list[str]
