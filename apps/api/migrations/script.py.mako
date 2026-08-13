"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

Impacto financeiro: descrever se altera cálculo, período fechado ou histórico.
Reversível: sim/não — se não, justificar.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.platform.db.types.utc_datetime import UtcDateTime  # noqa: F401
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | None = ${repr(branch_labels)}
depends_on: str | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
