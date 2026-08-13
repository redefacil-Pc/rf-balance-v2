"""Persistência de colaborador, papéis vigentes e chave PIX.

Listagem por cursor e papéis resolvidos em uma consulta por página — não uma por
colaborador (N+1 é o que deixou o v1 lento).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import Select, and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.infrastructure.models.user_model import UserModel
from app.modules.organization.infrastructure.models.collaborator_model import CollaboratorModel
from app.modules.organization.infrastructure.models.collaborator_payment_key_model import (
    CollaboratorPaymentKeyModel,
)
from app.modules.organization.infrastructure.models.collaborator_role_model import (
    CollaboratorRoleModel,
)
from app.platform.http.pagination import Cursor


@dataclass(frozen=True, slots=True)
class FiltroDeColaboradores:
    """Filtros da seção 7.2: papel, regime, unidade, empresa e situação."""

    company_id: int | None = None
    unit_id: int | None = None
    papel: str | None = None
    regime: str | None = None
    somente_ativos: bool | None = None
    busca_por_nome: str | None = None
    #: escopo do RBAC: quando presente, restringe às unidades permitidas
    unidades_permitidas: tuple[int, ...] | None = None
    somente_com_conta_ativa: bool = False


class SqlCollaboratorRepository:
    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def criar(
        self,
        *,
        company_id: int,
        unit_id: int | None,
        full_name: str,
        document_encrypted: str,
        document_hash: str,
        document_type: str,
        tax_regime: str,
        email: str | None,
        phone: str | None,
        ator: int | None,
    ) -> CollaboratorModel:
        modelo = CollaboratorModel(
            company_id=company_id,
            unit_id=unit_id,
            full_name=full_name,
            document_encrypted=document_encrypted,
            document_hash=document_hash,
            document_type=document_type,
            tax_regime=tax_regime,
            email=email,
            phone=phone,
            created_by=ator,
            updated_by=ator,
        )
        self._session.add(modelo)
        await self._session.flush()
        return modelo

    async def buscar_por_id(self, collaborator_id: int) -> CollaboratorModel | None:
        encontrado: CollaboratorModel | None = await self._session.scalar(
            select(CollaboratorModel).where(CollaboratorModel.id == collaborator_id)
        )
        return encontrado

    async def colaborador_da_conta(self, user_id: int) -> CollaboratorModel | None:
        """Quem é a pessoa por trás desta conta.

        É a pergunta que sustenta o escopo de dados: sem resposta, não há como
        distinguir "meus resultados" de "os resultados de todos".
        """
        encontrado: CollaboratorModel | None = await self._session.scalar(
            select(CollaboratorModel).where(CollaboratorModel.user_id == user_id)
        )
        return encontrado

    async def definir_conta(self, *, collaborator_id: int, user_id: int | None) -> None:
        await self._session.execute(
            update(CollaboratorModel)
            .where(CollaboratorModel.id == collaborator_id)
            .values(user_id=user_id)
        )

    async def nomes_por_id(self, ids: Sequence[int]) -> dict[int, str]:
        """Resolve nomes de uma página inteira em uma consulta — quem lista
        proposta precisa do nome do consultor, não do cadastro completo."""
        if not ids:
            return {}

        linhas = (
            await self._session.execute(
                select(CollaboratorModel.id, CollaboratorModel.full_name).where(
                    CollaboratorModel.id.in_(ids)
                )
            )
        ).all()
        return {int(identificador): str(nome) for identificador, nome in linhas}

    async def existe_documento(self, document_hash: str) -> bool:
        encontrado = await self._session.scalar(
            select(CollaboratorModel.id).where(CollaboratorModel.document_hash == document_hash)
        )
        return encontrado is not None

    async def inativar(
        self,
        *,
        collaborator_id: int,
        em: date,
        motivo: str,
        quando: datetime,
        ator: int | None,
    ) -> None:
        await self._session.execute(
            update(CollaboratorModel)
            .where(CollaboratorModel.id == collaborator_id)
            .values(
                is_active=False,
                deactivated_on=em,
                deactivation_reason=motivo,
                updated_at=quando,
                updated_by=ator,
                version=CollaboratorModel.version + 1,
            )
        )

    async def atualizar_cadastro(
        self,
        *,
        collaborator_id: int,
        company_id: int,
        unit_id: int | None,
        full_name: str,
        tax_regime: str,
        ator: int | None,
    ) -> None:
        await self._session.execute(
            update(CollaboratorModel)
            .where(CollaboratorModel.id == collaborator_id)
            .values(
                company_id=company_id,
                unit_id=unit_id,
                full_name=full_name,
                tax_regime=tax_regime,
                updated_by=ator,
                version=CollaboratorModel.version + 1,
            )
        )

    # ---------- papéis ----------

    async def adicionar_papel(
        self,
        *,
        collaborator_id: int,
        papel: str,
        valid_from: date,
        valid_to: date | None,
        ator: int | None,
    ) -> CollaboratorRoleModel:
        modelo = CollaboratorRoleModel(
            collaborator_id=collaborator_id,
            role=papel,
            valid_from=valid_from,
            valid_to=valid_to,
            created_by=ator,
        )
        self._session.add(modelo)
        await self._session.flush()
        return modelo

    async def encerrar_papel(self, *, function_id: int, valid_to: date) -> None:
        """Fecha a vigência da função. Não apaga a linha: o histórico é o que
        permite comissionar uma proposta antiga pela função da época.

        Quem encerrou fica na auditoria — `collaborator_roles` não tem coluna de
        atualização, e inventar uma só para isso duplicaria a trilha.
        """
        await self._session.execute(
            update(CollaboratorRoleModel)
            .where(CollaboratorRoleModel.id == function_id)
            .values(valid_to=valid_to)
        )
        await self._session.flush()

    async def papeis_do_colaborador(
        self, collaborator_id: int, *, papel: str | None = None
    ) -> list[CollaboratorRoleModel]:
        consulta = select(CollaboratorRoleModel).where(
            CollaboratorRoleModel.collaborator_id == collaborator_id
        )
        if papel is not None:
            consulta = consulta.where(CollaboratorRoleModel.role == papel)
        return list((await self._session.scalars(consulta)).all())

    async def papeis_vigentes_em(
        self, collaborator_id: int, referencia: date
    ) -> list[CollaboratorRoleModel]:
        """Consulta canônica de vigência (ADR-0013)."""
        consulta = select(CollaboratorRoleModel).where(
            CollaboratorRoleModel.collaborator_id == collaborator_id,
            CollaboratorRoleModel.valid_from <= referencia,
            or_(
                CollaboratorRoleModel.valid_to.is_(None),
                CollaboratorRoleModel.valid_to >= referencia,
            ),
        )
        return list((await self._session.scalars(consulta)).all())

    async def papeis_vigentes_de_varios(
        self, ids: Sequence[int], referencia: date
    ) -> dict[int, list[str]]:
        """Uma consulta para a página inteira, em vez de uma por linha."""
        if not ids:
            return {}

        linhas = (
            await self._session.execute(
                select(CollaboratorRoleModel.collaborator_id, CollaboratorRoleModel.role).where(
                    CollaboratorRoleModel.collaborator_id.in_(ids),
                    CollaboratorRoleModel.valid_from <= referencia,
                    or_(
                        CollaboratorRoleModel.valid_to.is_(None),
                        CollaboratorRoleModel.valid_to >= referencia,
                    ),
                )
            )
        ).all()

        agrupado: dict[int, list[str]] = {}
        for collaborator_id, papel in linhas:
            agrupado.setdefault(int(collaborator_id), []).append(str(papel))
        return agrupado

    # ---------- chave PIX ----------

    async def registrar_chave_pix(
        self,
        *,
        collaborator_id: int,
        key_type: str,
        key_encrypted: str,
        key_hash: str,
        key_masked: str,
        valid_from: date,
        ator: int | None,
    ) -> CollaboratorPaymentKeyModel:
        modelo = CollaboratorPaymentKeyModel(
            collaborator_id=collaborator_id,
            key_type=key_type,
            key_encrypted=key_encrypted,
            key_hash=key_hash,
            key_masked=key_masked,
            valid_from=valid_from,
            created_by=ator,
        )
        self._session.add(modelo)
        await self._session.flush()
        return modelo

    async def encerrar_chaves_vigentes(self, *, collaborator_id: int, em: date) -> None:
        """Troca de PIX não sobrescreve: encerra a vigência da anterior."""
        await self._session.execute(
            update(CollaboratorPaymentKeyModel)
            .where(
                CollaboratorPaymentKeyModel.collaborator_id == collaborator_id,
                CollaboratorPaymentKeyModel.valid_to.is_(None),
            )
            .values(valid_to=em)
        )

    async def chave_vigente(
        self, collaborator_id: int, referencia: date
    ) -> CollaboratorPaymentKeyModel | None:
        encontrada: CollaboratorPaymentKeyModel | None = await self._session.scalar(
            select(CollaboratorPaymentKeyModel)
            .where(
                CollaboratorPaymentKeyModel.collaborator_id == collaborator_id,
                CollaboratorPaymentKeyModel.valid_from <= referencia,
                or_(
                    CollaboratorPaymentKeyModel.valid_to.is_(None),
                    CollaboratorPaymentKeyModel.valid_to >= referencia,
                ),
            )
            .order_by(CollaboratorPaymentKeyModel.valid_from.desc())
        )
        return encontrada

    # ---------- listagem ----------

    async def listar(
        self,
        *,
        filtro: FiltroDeColaboradores,
        limite: int,
        cursor: Cursor | None,
        referencia: date,
    ) -> tuple[list[CollaboratorModel], bool]:
        """Ordena por (nome, id) — o par é estável e sustenta o cursor."""
        consulta = self._aplicar_filtros(select(CollaboratorModel), filtro, referencia)

        if cursor is not None:
            consulta = consulta.where(
                or_(
                    CollaboratorModel.full_name > cursor.chave,
                    and_(
                        CollaboratorModel.full_name == cursor.chave,
                        CollaboratorModel.id > cursor.id,
                    ),
                )
            )

        consulta = consulta.order_by(CollaboratorModel.full_name, CollaboratorModel.id).limit(
            limite + 1
        )
        encontrados = list((await self._session.scalars(consulta)).all())

        tem_mais = len(encontrados) > limite
        return encontrados[:limite], tem_mais

    def _aplicar_filtros(
        self,
        consulta: Select[tuple[CollaboratorModel]],
        filtro: FiltroDeColaboradores,
        referencia: date,
    ) -> Select[tuple[CollaboratorModel]]:
        if filtro.somente_com_conta_ativa:
            consulta = consulta.join(UserModel, UserModel.id == CollaboratorModel.user_id).where(
                UserModel.is_active.is_(True)
            )
        if filtro.company_id is not None:
            consulta = consulta.where(CollaboratorModel.company_id == filtro.company_id)
        if filtro.unit_id is not None:
            consulta = consulta.where(CollaboratorModel.unit_id == filtro.unit_id)
        if filtro.regime is not None:
            consulta = consulta.where(CollaboratorModel.tax_regime == filtro.regime)
        if filtro.somente_ativos is not None:
            consulta = consulta.where(CollaboratorModel.is_active.is_(filtro.somente_ativos))
        if filtro.busca_por_nome:
            consulta = consulta.where(CollaboratorModel.full_name.like(f"{filtro.busca_por_nome}%"))
        if filtro.unidades_permitidas is not None:
            # escopo do RBAC aplicado em SQL, nunca filtrado no cliente
            consulta = consulta.where(CollaboratorModel.unit_id.in_(filtro.unidades_permitidas))
        if filtro.papel is not None:
            vigentes = (
                select(CollaboratorRoleModel.collaborator_id)
                .where(
                    CollaboratorRoleModel.role == filtro.papel,
                    CollaboratorRoleModel.valid_from <= referencia,
                    or_(
                        CollaboratorRoleModel.valid_to.is_(None),
                        CollaboratorRoleModel.valid_to >= referencia,
                    ),
                )
                .scalar_subquery()
            )
            consulta = consulta.where(CollaboratorModel.id.in_(vigentes))
        return consulta
