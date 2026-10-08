"""ipos

Revision ID: b1e6c9a2f0d4
Revises: 9d383904ae36
Create Date: 2026-10-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1e6c9a2f0d4'
down_revision: Union[str, Sequence[str], None] = '9d383904ae36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ipos',
        sa.Column('ipo_id', sa.String(), nullable=False),
        sa.Column('company_name', sa.String(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('board', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('exchange', sa.String(), nullable=False),
        sa.Column('open_date', sa.Date(), nullable=True),
        sa.Column('close_date', sa.Date(), nullable=True),
        sa.Column('listing_date', sa.Date(), nullable=True),
        sa.Column('price_band_low', sa.Numeric(14, 2), nullable=True),
        sa.Column('price_band_high', sa.Numeric(14, 2), nullable=True),
        sa.Column('lot_size', sa.Integer(), nullable=True),
        sa.Column('face_value', sa.Numeric(14, 2), nullable=True),
        sa.Column('issue_size_cr', sa.Numeric(14, 2), nullable=True),
        sa.Column('fresh_issue_cr', sa.Numeric(14, 2), nullable=True),
        sa.Column('ofs_cr', sa.Numeric(14, 2), nullable=True),
        sa.Column('registrar', sa.String(), nullable=True),
        sa.Column('lead_managers', sa.JSON(), nullable=False),
        sa.Column('about', sa.Text(), nullable=True),
        sa.Column('report_text', sa.Text(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('ipo_id'),
    )
    with op.batch_alter_table('ipos', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ipos_symbol'), ['symbol'], unique=True)
        batch_op.create_index(batch_op.f('ix_ipos_board'), ['board'], unique=False)
        batch_op.create_index(batch_op.f('ix_ipos_status'), ['status'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('ipos', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ipos_status'))
        batch_op.drop_index(batch_op.f('ix_ipos_board'))
        batch_op.drop_index(batch_op.f('ix_ipos_symbol'))
    op.drop_table('ipos')
