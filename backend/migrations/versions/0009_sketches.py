"""sketches: quick recordings that may ask for feedback

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0009'
down_revision: Union[str, None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('posts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('seeking_feedback', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('posts', schema=None) as batch_op:
        batch_op.drop_column('seeking_feedback')
