"""Consulta paginada da trilha de auditoria append-only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.infrastructure.models.audit_event_model import AuditEventModel
from app.modules.identity.infrastructure.models.user_model import UserModel
from app.platform.http.pagination import Cursor, Pagina


@dataclass(frozen=True, slots=True)
class AuditFilters:
    start_date: date | None = None
    end_date: date | None = None
    module: str | None = None
    action: str | None = None
    actor: str | None = None
    aggregate_type: str | None = None
    aggregate_id: str | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class AuditEventView:
    id: int
    occurred_at: datetime
    business_date: date
    module: str
    action: str
    actor_user_id: int | None
    actor_name: str
    aggregate_type: str | None
    aggregate_id: str | None
    correlation_id: str | None
    payload: dict[str, Any]


class ListAuditEventsQuery:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(
        self, *, filters: AuditFilters, limit: int, cursor: Cursor | None
    ) -> Pagina[AuditEventView]:
        query = (
            select(AuditEventModel, UserModel.full_name)
            .outerjoin(UserModel, UserModel.id == AuditEventModel.actor_user_id)
            .order_by(AuditEventModel.id.desc())
            .limit(limit + 1)
        )
        if filters.start_date is not None:
            query = query.where(AuditEventModel.business_date >= filters.start_date)
        if filters.end_date is not None:
            query = query.where(AuditEventModel.business_date <= filters.end_date)
        if filters.module:
            query = query.where(AuditEventModel.module == filters.module)
        if filters.action:
            query = query.where(AuditEventModel.action.like(f"{filters.action}%"))
        if filters.actor:
            query = query.where(
                or_(
                    UserModel.full_name.like(f"%{filters.actor}%"),
                    AuditEventModel.actor_label.like(f"%{filters.actor}%"),
                )
            )
        if filters.aggregate_type:
            query = query.where(AuditEventModel.aggregate_type == filters.aggregate_type)
        if filters.aggregate_id:
            query = query.where(AuditEventModel.aggregate_id == filters.aggregate_id)
        if filters.correlation_id:
            query = query.where(AuditEventModel.correlation_id.like(f"{filters.correlation_id}%"))
        if cursor is not None:
            query = query.where(AuditEventModel.id < cursor.id)

        rows = (await self._session.execute(query)).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        items = [
            AuditEventView(
                id=event.id,
                occurred_at=event.occurred_at,
                business_date=event.business_date,
                module=event.module,
                action=event.action,
                actor_user_id=event.actor_user_id,
                actor_name=str(actor_name or event.actor_label or "Sistema"),
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                correlation_id=event.correlation_id,
                payload=event.payload,
            )
            for event, actor_name in rows
        ]
        next_cursor = None
        if has_more and items:
            next_cursor = Cursor(chave=str(items[-1].id), id=items[-1].id).codificar()
        return Pagina(itens=items, proximo_cursor=next_cursor)

    async def options(self) -> tuple[list[str], list[str], list[str]]:
        modules = list(
            (
                await self._session.scalars(
                    select(AuditEventModel.module).distinct().order_by(AuditEventModel.module)
                )
            ).all()
        )
        actions = list(
            (
                await self._session.scalars(
                    select(AuditEventModel.action).distinct().order_by(AuditEventModel.action)
                )
            ).all()
        )
        aggregates = list(
            (
                await self._session.scalars(
                    select(AuditEventModel.aggregate_type)
                    .where(AuditEventModel.aggregate_type.is_not(None))
                    .distinct()
                    .order_by(AuditEventModel.aggregate_type)
                )
            ).all()
        )
        return modules, actions, [str(item) for item in aggregates]
