"""Tabela `collaborator_roles` — funções com vigência (ADR-0013).

Uma linha por papel, com intervalo fechado `[valid_from, valid_to]`. É o que
permite a uma pessoa acumular funções sem enum combinatório e ao motor de
comissão saber qual papel valia numa data passada.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA
from app.platform.db.types.utc_datetime import UtcDateTime


class CollaboratorRoleModel(Base):
    __tablename__ = "collaborator_roles"
    __table_args__ = (
        # caminho de acesso da consulta histórica: papel vigente numa data
        Index(
            "ix_collaborator_roles_collaborator_id_role_valid_from",
            "collaborator_id",
            "role",
            "valid_from",
        ),
        Index("ix_collaborator_roles_role_valid_from", "role", "valid_from"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    collaborator_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("collaborators.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    # NULL = vigente, sem fim previsto
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
