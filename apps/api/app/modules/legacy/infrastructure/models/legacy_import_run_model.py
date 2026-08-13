"""Tabela `legacy_import_runs` — uma linha por execução do importador.

Guardar a execução é o que torna o relatório de divergência comparável entre
rodadas: "o que mudou desde a semana passada" é a pergunta que decide se o
cutover pode acontecer. Em `dry_run` nenhuma tabela canônica é tocada.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA
from app.platform.db.types.utc_datetime import UtcDateTime


class LegacyImportRunModel(Base):
    __tablename__ = "legacy_import_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    #: `csv:/caminho` ou `mysql:<host>/<database>` — sem credencial
    source_label: Mapped[str] = mapped_column(String(200), nullable=False)
    #: falso só na carga real da F7; na F2 é sempre verdadeiro
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    #: contagens e totais da reconciliação mínima (seção 18)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    triggered_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
