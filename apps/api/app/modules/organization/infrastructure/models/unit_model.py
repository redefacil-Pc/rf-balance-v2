"""Tabela `units` — unidades vinculadas à empresa.

A unidade é a fronteira de escopo de dados mais usada pelo RBAC: gestor de
unidade vê a sua, não a do vizinho.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA, AGORA_COM_ON_UPDATE
from app.platform.db.types.utc_datetime import UtcDateTime


class UnitModel(Base):
    __tablename__ = "units"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_units_company_id_code"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, server_default=AGORA_COM_ON_UPDATE
    )
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
