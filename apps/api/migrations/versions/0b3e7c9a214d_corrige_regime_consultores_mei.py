"""registra separação entre regime e função do consultor

Revision ID: 0b3e7c9a214d
Revises: f86c02deb173
"""

revision = "0b3e7c9a214d"
down_revision = "f86c02deb173"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Migração-marco sem alteração de dados: MEI e CLT são válidos para qualquer
    # função de consultor; a função vigente é quem seleciona o motor de comissão.
    pass


def downgrade() -> None:
    pass
