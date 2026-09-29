"""uploads: who stored what and when, for the daily upload limit

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0010'
down_revision: Union[str, None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'uploads',
        sa.Column('key', sa.String(length=512), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('size', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('key'),
    )
    op.create_index('ix_uploads_user_id', 'uploads', ['user_id'], unique=False)
    op.create_index('ix_uploads_created_at', 'uploads', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_uploads_created_at', table_name='uploads')
    op.drop_index('ix_uploads_user_id', table_name='uploads')
    op.drop_table('uploads')
