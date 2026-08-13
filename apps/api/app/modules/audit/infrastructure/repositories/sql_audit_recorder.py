"""Gravação de auditoria em `audit_events`, na transação do caso de uso."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.infrastructure.models.audit_event_model import AuditEventModel
from app.platform.time.clock import Clock


class SqlAuditRecorder:
    __slots__ = ("_clock", "_session")

    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def registrar(
        self,
        *,
        module: str,
        action: str,
        actor_user_id: int | None = None,
        actor_label: str = "",
        aggregate_type: str | None = None,
        aggregate_id: str | None = None,
        correlation_id: str | None = None,
        ip_hash: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._session.add(
            AuditEventModel(
                occurred_at=self._clock.now(),
                business_date=self._clock.business_date(),
                module=module,
                action=action,
                actor_user_id=actor_user_id,
                actor_label=actor_label,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                correlation_id=correlation_id,
                ip_hash=ip_hash,
                payload=payload or {},
            )
        )
