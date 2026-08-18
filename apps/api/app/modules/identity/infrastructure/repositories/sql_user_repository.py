"""Persistência de usuário em MySQL.

Papéis e permissões são resolvidos em **uma** consulta com join, não em três —
esse é exatamente o N+1 que a Trilha P proíbe.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.domain.entities.user import User
from app.modules.identity.domain.value_objects.email_address import EmailAddress
from app.modules.identity.infrastructure.models.permission_model import PermissionModel
from app.modules.identity.infrastructure.models.role_model import RoleModel
from app.modules.identity.infrastructure.models.role_permission_model import RolePermissionModel
from app.modules.identity.infrastructure.models.user_model import UserModel
from app.modules.identity.infrastructure.models.user_role_model import UserRoleModel
from app.modules.organization.infrastructure.models.collaborator_model import CollaboratorModel
from app.platform.http.pagination import Cursor


@dataclass(frozen=True, slots=True)
class FiltroDeUsuarios:
    papel: str | None = None
    somente_ativos: bool | None = None
    busca: str | None = None
    #: `False` devolve só quem ainda não tem colaborador — é a lista de contas
    #: vinculáveis na criação de um colaborador
    com_colaborador: bool | None = None


class SqlUserRepository:
    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def buscar_por_email(self, email: EmailAddress) -> User | None:
        modelo = await self._session.scalar(select(UserModel).where(UserModel.email == email.valor))
        return await self._montar(modelo)

    async def buscar_por_id(self, user_id: int) -> User | None:
        modelo = await self._session.scalar(select(UserModel).where(UserModel.id == user_id))
        return await self._montar(modelo)

    async def registrar_acesso(self, user_id: int, quando: datetime) -> None:
        await self._session.execute(
            update(UserModel).where(UserModel.id == user_id).values(last_login_at=quando)
        )

    async def atualizar_hash(self, user_id: int, novo_hash: str) -> None:
        await self._session.execute(
            update(UserModel).where(UserModel.id == user_id).values(password_hash=novo_hash)
        )

    # ---------- escrita de cadastro ----------

    async def criar(
        self,
        *,
        email: EmailAddress,
        full_name: str,
        password_hash: str,
        must_change_password: bool,
    ) -> UserModel:
        modelo = UserModel(
            email=email.valor,
            full_name=full_name,
            password_hash=password_hash,
            is_active=True,
            must_change_password=must_change_password,
        )
        self._session.add(modelo)
        await self._session.flush()
        return modelo

    async def linha(self, user_id: int) -> UserModel | None:
        encontrada: UserModel | None = await self._session.scalar(
            select(UserModel).where(UserModel.id == user_id)
        )
        return encontrada

    async def existe_email(self, email: EmailAddress, *, exceto: int | None = None) -> bool:
        consulta = select(UserModel.id).where(UserModel.email == email.valor)
        if exceto is not None:
            consulta = consulta.where(UserModel.id != exceto)
        return await self._session.scalar(consulta) is not None

    async def definir_senha(self, user_id: int, *, novo_hash: str, exigir_troca: bool) -> None:
        await self._session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(password_hash=novo_hash, must_change_password=exigir_troca)
        )

    # ---------- papéis ----------

    async def papeis_por_codigo(self, codigos: Sequence[str]) -> dict[str, RoleModel]:
        if not codigos:
            return {}
        encontrados = await self._session.scalars(
            select(RoleModel).where(RoleModel.code.in_(tuple(codigos)))
        )
        return {r.code: r for r in encontrados.all()}

    async def substituir_papeis(self, user_id: int, role_ids: Sequence[int]) -> None:
        """Troca o conjunto inteiro: a intenção do cliente é o estado final,
        não um delta — assim duas telas não somam papéis sem querer."""
        await self._session.execute(delete(UserRoleModel).where(UserRoleModel.user_id == user_id))
        for role_id in role_ids:
            self._session.add(UserRoleModel(user_id=user_id, role_id=role_id))
        await self._session.flush()

    async def colaboradores_de_varios(self, ids: Sequence[int]) -> dict[int, int]:
        """Conta -> colaborador, para a página inteira numa consulta.

        O vínculo mora em `collaborators.user_id`; ler daqui é a alternativa a
        duplicar a coluna em `users`, que fecharia um ciclo de FK entre as duas
        tabelas.
        """
        if not ids:
            return {}
        linhas = (
            await self._session.execute(
                select(CollaboratorModel.user_id, CollaboratorModel.id).where(
                    CollaboratorModel.user_id.in_(tuple(ids))
                )
            )
        ).all()
        return {int(user_id): int(colaborador) for user_id, colaborador in linhas}

    async def papeis_de_varios(self, ids: Sequence[int]) -> dict[int, list[str]]:
        """Uma consulta para a página inteira, não uma por usuário."""
        if not ids:
            return {}
        linhas = (
            await self._session.execute(
                select(UserRoleModel.user_id, RoleModel.code)
                .join(RoleModel, RoleModel.id == UserRoleModel.role_id)
                .where(UserRoleModel.user_id.in_(tuple(ids)))
            )
        ).all()

        agrupado: dict[int, list[str]] = {}
        for user_id, code in linhas:
            agrupado.setdefault(int(user_id), []).append(str(code))
        for papeis in agrupado.values():
            papeis.sort()
        return agrupado

    # ---------- listagem ----------

    async def listar(
        self, *, filtro: FiltroDeUsuarios, limite: int, cursor: Cursor | None
    ) -> tuple[list[UserModel], bool]:
        """Ordena por (nome, id): o par é estável e sustenta o cursor."""
        consulta = select(UserModel)

        if filtro.somente_ativos is not None:
            consulta = consulta.where(UserModel.is_active.is_(filtro.somente_ativos))
        if filtro.busca:
            termo = f"{filtro.busca}%"
            consulta = consulta.where(
                or_(UserModel.full_name.like(termo), UserModel.email.like(termo))
            )
        if filtro.papel is not None:
            com_o_papel = (
                select(UserRoleModel.user_id)
                .join(RoleModel, RoleModel.id == UserRoleModel.role_id)
                .where(RoleModel.code == filtro.papel)
                .scalar_subquery()
            )
            consulta = consulta.where(UserModel.id.in_(com_o_papel))
        if filtro.com_colaborador is not None:
            vinculadas = select(CollaboratorModel.user_id).where(
                CollaboratorModel.user_id.is_not(None)
            )
            consulta = consulta.where(
                UserModel.id.in_(vinculadas)
                if filtro.com_colaborador
                else UserModel.id.not_in(vinculadas)
            )

        if cursor is not None:
            consulta = consulta.where(
                or_(
                    UserModel.full_name > cursor.chave,
                    and_(UserModel.full_name == cursor.chave, UserModel.id > cursor.id),
                )
            )

        consulta = consulta.order_by(UserModel.full_name, UserModel.id).limit(limite + 1)
        encontrados = list((await self._session.scalars(consulta)).all())
        return encontrados[:limite], len(encontrados) > limite

    async def atualizar_cadastro(
        self, user_id: int, *, email: EmailAddress, full_name: str
    ) -> None:
        await self._session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(email=email.valor, full_name=full_name)
        )

    async def definir_situacao(self, user_id: int, *, ativo: bool) -> None:
        await self._session.execute(
            update(UserModel).where(UserModel.id == user_id).values(is_active=ativo)
        )

    async def _montar(self, modelo: UserModel | None) -> User | None:
        if modelo is None:
            return None

        linhas = (
            await self._session.execute(
                select(RoleModel.code, PermissionModel.code)
                .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
                .outerjoin(RolePermissionModel, RolePermissionModel.role_id == RoleModel.id)
                .outerjoin(PermissionModel, PermissionModel.id == RolePermissionModel.permission_id)
                .where(UserRoleModel.user_id == modelo.id)
            )
        ).all()

        return User(
            id=modelo.id,
            email=EmailAddress(modelo.email),
            full_name=modelo.full_name,
            password_hash=modelo.password_hash,
            is_active=modelo.is_active,
            must_change_password=modelo.must_change_password,
            roles=frozenset(papel for papel, _ in linhas),
            permissions=frozenset(permissao for _, permissao in linhas if permissao),
        )
