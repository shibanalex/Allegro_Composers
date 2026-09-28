"""session versions (sign out everywhere) and indexes for halls and feeds

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('session_version', sa.Integer(), server_default='0', nullable=False))
    op.create_index('ix_posts_author_kind_created', 'posts', ['author_id', 'kind', 'created_at'], unique=False)
    op.create_index('ix_opuses_author_status_created', 'opuses', ['author_id', 'status', 'created_at'], unique=False)
    op.create_index('ix_performances_performer_created', 'performances', ['performer_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_performances_performer_created', table_name='performances')
    op.drop_index('ix_opuses_author_status_created', table_name='opuses')
    op.drop_index('ix_posts_author_kind_created', table_name='posts')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('session_version')
