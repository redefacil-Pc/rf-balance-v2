"""comercial propostas

Revision ID: b3c1d9a47f52
Revises: 0587408f5e7f
Create Date: 2026-08-12 09:15:00.000000

Cria `proposals`, o aggregate comercial único da seção 7.4. Documento do cliente
em par cifrado + hash de busca (ADR-0012); o hash **não** é único, porque o mesmo
cliente pode ter várias propostas — a unicidade que importa é `external_id`
(Redmine), garantida no banco e não só no handler.

Impacto financeiro: alto. `company_commission_amount` é a base de todo o
comissionamento da F4; `paid_amount_cached` e `outstanding_amount_cached` são
cache do que `receipts` vai consolidar na F3, e a divergência entre eles é
verificada em `data_integrity_checks`, não corrigida em silêncio.

Reversível: sim, enquanto não existir recebimento ou lançamento de comissão
apontando para proposta — a partir da F3 o `downgrade` deixa de ser aceitável em
produção e a correção passa a ser migração compensatória.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.platform.db.types.utc_datetime import UtcDateTime  # noqa: F401


revision: str = 'b3c1d9a47f52'
down_revision: str | None = '0587408f5e7f'
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table('proposals',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('external_id', sa.String(length=60), nullable=True),
    sa.Column('consultant_id', sa.BigInteger(), nullable=False),
    sa.Column('bko_collaborator_id', sa.BigInteger(), nullable=True),
    sa.Column('finalizer_collaborator_id', sa.BigInteger(), nullable=True),
    sa.Column('business_date', sa.Date(), nullable=False),
    sa.Column('customer_name', sa.String(length=200), nullable=False),
    sa.Column('customer_document_encrypted', sa.String(length=255), nullable=False),
    sa.Column('customer_document_hash', sa.String(length=64), nullable=False),
    sa.Column('customer_document_type', sa.String(length=4), nullable=False),
    sa.Column('operation_amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('tps_percentage', sa.Numeric(precision=9, scale=6), nullable=False),
    sa.Column('company_commission_amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('paid_amount_cached', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('outstanding_amount_cached', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('tolerance_policy_version', sa.String(length=20), nullable=False),
    sa.Column('commission_snapshot_id', sa.BigInteger(), nullable=True),
    sa.Column('created_at', UtcDateTime(), server_default=sa.text('CURRENT_TIMESTAMP(6)'), nullable=False),
    sa.Column('created_by', sa.BigInteger(), nullable=True),
    sa.Column('updated_at', UtcDateTime(), server_default=sa.text('CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)'), nullable=False),
    sa.Column('updated_by', sa.BigInteger(), nullable=True),
    sa.Column('settled_at', UtcDateTime(), nullable=True),
    sa.Column('cancelled_at', UtcDateTime(), nullable=True),
    sa.Column('cancellation_reason', sa.String(length=255), nullable=True),
    sa.Column('version', sa.BigInteger(), nullable=False),
    sa.CheckConstraint('operation_amount > 0', name=op.f('ck_proposals_operation_amount_positivo')),
    sa.CheckConstraint('tps_percentage >= 0 AND tps_percentage <= 100', name=op.f('ck_proposals_tps_percentage')),
    sa.ForeignKeyConstraint(['bko_collaborator_id'], ['collaborators.id'], name=op.f('fk_proposals_bko_collaborator_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['consultant_id'], ['collaborators.id'], name=op.f('fk_proposals_consultant_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['finalizer_collaborator_id'], ['collaborators.id'], name=op.f('fk_proposals_finalizer_collaborator_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_proposals')),
    sa.UniqueConstraint('external_id', name=op.f('uq_proposals_external_id'))
    )
    op.create_index('ix_proposals_consultant_id_business_date', 'proposals', ['consultant_id', 'business_date'], unique=False)
    op.create_index('ix_proposals_customer_document_hash', 'proposals', ['customer_document_hash'], unique=False)
    op.create_index('ix_proposals_status_business_date', 'proposals', ['status', 'business_date'], unique=False)


def downgrade() -> None:
    # `drop_table` remove os índices da própria tabela; dropar índice que
    # sustenta FK antes disso faz o MySQL recusar com erro 1553.
    op.drop_table('proposals')
