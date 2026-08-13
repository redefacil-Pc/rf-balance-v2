"""Persistência de empresas e unidades.

Empresa e unidade são cadastros simples: sem aggregate, sem repositório por
entidade separada (a skill de arquitetura chama isso de cerimônia sem regra).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organization.infrastructure.models.company_model import CompanyModel
from app.modules.organization.infrastructure.models.unit_model import UnitModel


class SqlCompanyRepository:
    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def criar(
        self,
        *,
        legal_name: str,
        trade_name: str,
        document_encrypted: str | None,
        document_hash: str | None,
        ator: int | None,
    ) -> CompanyModel:
        modelo = CompanyModel(
            legal_name=legal_name,
            trade_name=trade_name,
            document_encrypted=document_encrypted,
            document_hash=document_hash,
            created_by=ator,
            updated_by=ator,
        )
        self._session.add(modelo)
        await self._session.flush()
        return modelo

    async def buscar_por_id(self, company_id: int) -> CompanyModel | None:
        encontrada: CompanyModel | None = await self._session.scalar(
            select(CompanyModel).where(CompanyModel.id == company_id)
        )
        return encontrada

    async def buscar_por_hash_de_documento(self, document_hash: str) -> CompanyModel | None:
        encontrada: CompanyModel | None = await self._session.scalar(
            select(CompanyModel).where(CompanyModel.document_hash == document_hash)
        )
        return encontrada

    async def listar(self, *, somente_ativas: bool) -> list[CompanyModel]:
        consulta = select(CompanyModel).order_by(CompanyModel.legal_name)
        if somente_ativas:
            consulta = consulta.where(CompanyModel.is_active.is_(True))
        return list((await self._session.scalars(consulta)).all())

    async def criar_unidade(
        self,
        *,
        company_id: int,
        code: str,
        name: str,
        ator: int | None,
    ) -> UnitModel:
        modelo = UnitModel(
            company_id=company_id, code=code, name=name, created_by=ator, updated_by=ator
        )
        self._session.add(modelo)
        await self._session.flush()
        return modelo

    async def buscar_unidade(self, unit_id: int) -> UnitModel | None:
        encontrada: UnitModel | None = await self._session.scalar(
            select(UnitModel).where(UnitModel.id == unit_id)
        )
        return encontrada

    async def listar_unidades(
        self, *, company_id: int | None, somente_ativas: bool
    ) -> list[UnitModel]:
        consulta = select(UnitModel).order_by(UnitModel.name)
        if company_id is not None:
            consulta = consulta.where(UnitModel.company_id == company_id)
        if somente_ativas:
            consulta = consulta.where(UnitModel.is_active.is_(True))
        return list((await self._session.scalars(consulta)).all())
