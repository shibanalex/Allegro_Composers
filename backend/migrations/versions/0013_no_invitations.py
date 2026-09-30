"""registration is open to everyone: invitations are gone

- access_links keeps only password-reset links: invitations are deleted, with their columns (role, used_by_id)
- users.invited_by_id is dropped

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0013'
down_revision: Union[str, None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM access_links WHERE purpose = 'invite'")
    with op.batch_alter_table('access_links', schema=None) as batch_op:
        batch_op.drop_column('used_by_id')
        batch_op.drop_column('role')
    # The key's name as the database knows it (fk_users_invited_by when made by 0006)
    keys = [fk['name'] for fk in sa.inspect(op.get_bind()).get_foreign_keys('users')
            if fk['constrained_columns'] == ['invited_by_id'] and fk['name']]
    with op.batch_alter_table('users', schema=None) as batch_op:
        for name in keys:
            batch_op.drop_constraint(name, type_='foreignkey')
        batch_op.drop_column('invited_by_id')


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('invited_by_id', sa.Uuid(), nullable=True))
        batch_op.create_foreign_key('fk_users_invited_by', 'users', ['invited_by_id'], ['id'], ondelete='SET NULL')
    with op.batch_alter_table('access_links', schema=None) as batch_op:
        batch_op.add_column(sa.Column('role', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('used_by_id', sa.Uuid(), nullable=True))
        batch_op.create_foreign_key('fk_access_links_used_by', 'users', ['used_by_id'], ['id'], ondelete='SET NULL')
