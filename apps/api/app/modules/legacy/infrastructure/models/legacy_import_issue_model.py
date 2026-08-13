"""Tabela `legacy_import_issues` — a fila de exceção da importação.

Cada linha é um registro que o importador se recusou a resolver adivinhando
(seção 18). Append-only dentro de uma execução: correção gera execução nova, não
`UPDATE` na anterior — senão o relatório deixa de refletir o que foi visto.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base


class LegacyImportIssueModel(Base):
    __tablename__ = "legacy_import_issues"
    __table_args__ = (
        # "o que travou nesta rodada, do mais grave para o menos"
        Index("ix_legacy_import_issues_run_id_severity", "run_id", "severity"),
        # "o que houve com este registro do legado"
        Index("ix_legacy_import_issues_source_legacy_id", "source_table", "legacy_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("legacy_import_runs.id", ondelete="CASCADE"), nullable=False
    )
    source_table: Mapped[str] = mapped_column(String(40), nullable=False)
    legacy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    #: BLOQUEIO ou ATENCAO
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    detail: Mapped[str] = mapped_column(String(500), nullable=False)
    #: contexto para quem decide — sem documento nem chave PIX em claro
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
