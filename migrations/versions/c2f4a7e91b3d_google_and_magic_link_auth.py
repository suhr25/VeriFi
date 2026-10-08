"""google and magic link auth

Revision ID: c2f4a7e91b3d
Revises: b1e6c9a2f0d4
Create Date: 2026-10-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2f4a7e91b3d'
down_revision: Union[str, Sequence[str], None] = 'b1e6c9a2f0d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('password_hash', existing_type=sa.String(), nullable=True)

    op.create_table(
        'email_login_tokens',
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('token_hash'),
    )
    with op.batch_alter_table('email_login_tokens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_email_login_tokens_email'), ['email'], unique=False)
        batch_op.create_index(batch_op.f('ix_email_login_tokens_expires_at'), ['expires_at'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('email_login_tokens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_email_login_tokens_expires_at'))
        batch_op.drop_index(batch_op.f('ix_email_login_tokens_email'))
    op.drop_table('email_login_tokens')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('password_hash', existing_type=sa.String(), nullable=False)
