"""Persistência da execução do importador e da sua fila de exceção."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.legacy.domain.value_objects.issue import Issue
from app.modules.legacy.infrastructure.models.legacy_import_issue_model import (
    LegacyImportIssueModel,
)
from app.modules.legacy.infrastructure.models.legacy_import_run_model import LegacyImportRunModel

#: `detail` é VARCHAR(500) — texto maior é truncado aqui, não pelo banco
LIMITE_DO_DETALHE = 500


class SqlLegacyImportRepository:
    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def abrir_execucao(
        self, *, source_label: str, dry_run: bool, quando: datetime, ator: int | None
    ) -> LegacyImportRunModel:
        modelo = LegacyImportRunModel(
            started_at=quando,
            source_label=source_label,
            dry_run=dry_run,
            summary={},
            triggered_by=ator,
        )
        self._session.add(modelo)
        await self._session.flush()
        return modelo

    async def registrar_issues(self, *, run_id: int, issues: list[Issue]) -> None:
        for issue in issues:
            self._session.add(
                LegacyImportIssueModel(
                    run_id=run_id,
                    source_table=issue.origem,
                    legacy_id=issue.legacy_id,
                    code=issue.codigo.value,
                    severity=issue.severidade.value,
                    detail=issue.detalhe[:LIMITE_DO_DETALHE],
                    data=issue.dados,
                )
            )
        await self._session.flush()

    async def encerrar_execucao(
        self, execucao: LegacyImportRunModel, *, summary: dict[str, Any], quando: datetime
    ) -> None:
        execucao.summary = summary
        execucao.finished_at = quando
        await self._session.flush()
