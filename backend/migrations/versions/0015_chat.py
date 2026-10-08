"""the community chat: chat_messages

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0015'
down_revision: Union[str, None] = '0014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('room', sa.String(length=40), nullable=False),
        sa.Column('author_id', sa.Uuid(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_chat_messages_room_created', 'chat_messages', ['room', 'created_at'], unique=False)
    op.create_index(op.f('ix_chat_messages_author_id'), 'chat_messages', ['author_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_chat_messages_author_id'), table_name='chat_messages')
    op.drop_index('ix_chat_messages_room_created', table_name='chat_messages')
    op.drop_table('chat_messages')
