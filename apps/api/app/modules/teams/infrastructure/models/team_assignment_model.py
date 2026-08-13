"""Tabela `team_assignments` — vínculo temporal consultor-líder (seção 7.3).

Intervalo fechado `[start_date, end_date]`, `end_date` nulo = vigente
(ADR-0013). A proibição de sobreposição por consultor e tipo não tem constraint
declarativa no MySQL: é garantida no domínio e auditada por rotina periódica em
`data_integrity_checks`.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA
from app.platform.db.types.utc_datetime import UtcDateTime


class TeamAssignmentModel(Base):
    __tablename__ = "team_assignments"
    __table_args__ = (
        # caminho de acesso de "qual era o líder deste consultor na data X"
        Index(
            "ix_team_assignments_consultant_id_type_start_date",
            "consultant_id",
            "assignment_type",
            "start_date",
        ),
        # e de "quem era a equipe deste líder na data X"
        Index("ix_team_assignments_leader_id_start_date", "leader_id", "start_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    consultant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("collaborators.id", ondelete="RESTRICT"), nullable=False
    )
    leader_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("collaborators.id", ondelete="RESTRICT"), nullable=False
    )
    # COMERCIAL, MEI_GERAL ou FINALIZACAO — um consultor tem no máximo um
    # vínculo ativo por tipo
    assignment_type: Mapped[str] = mapped_column(String(20), nullable=False)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # motivo obrigatório em encerramento e correção (seção 7.3)
    closing_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
