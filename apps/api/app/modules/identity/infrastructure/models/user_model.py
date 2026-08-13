"""Tabela `users` — conta de acesso.

O vínculo com a pessoa mora em `collaborators.user_id`, não aqui: uma coluna só,
numa direção só. A recíproca (`users.collaborator_id`) fecharia um ciclo de
chaves estrangeiras entre as duas tabelas, com dois lugares para manter em
acordo e nenhum ganho — o join responde igual nos dois sentidos.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA, AGORA_COM_ON_UPDATE
from app.platform.db.types.utc_datetime import UtcDateTime


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # normalizado (trim + lower) na escrita; a unicidade é garantida pelo banco
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, server_default=AGORA_COM_ON_UPDATE
    )
