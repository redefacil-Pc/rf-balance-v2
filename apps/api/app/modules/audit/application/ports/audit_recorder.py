"""Porta de gravação de auditoria.

Definida pelo módulo dono de `audit_events`: os outros módulos dependem desta
interface, e nenhum deles escreve na tabela diretamente.
"""

from __future__ import annotations

from typing import Any, Protocol


class AuditRecorder(Protocol):
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
        """Enfileira o evento na transação corrente. O commit é do caso de uso."""
        ...
