"""notifications: the outbox of events, notifications, settings, push subscriptions

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0011'
down_revision: Union[str, None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'outbox',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('kind', sa.String(length=40), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_outbox_processed_at', 'outbox', ['processed_at'], unique=False)

    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('actor_id', sa.Uuid(), nullable=True),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('target_type', sa.String(length=20), nullable=False),
        sa.Column('target_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=512), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notifications_user_created', 'notifications', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_notifications_target', 'notifications', ['target_type', 'target_id'], unique=False)

    op.create_table(
        'notification_settings',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('kinds', sa.JSON(), nullable=False),
        sa.Column('push', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('email', sa.String(length=10), server_default='off', nullable=False),
        sa.Column('last_digest_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )

    op.create_table(
        'push_subscriptions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('endpoint', sa.String(length=1024), nullable=False),
        sa.Column('p256dh', sa.String(length=255), nullable=False),
        sa.Column('auth', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('endpoint'),
    )
    op.create_index('ix_push_subscriptions_user_id', 'push_subscriptions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_push_subscriptions_user_id', table_name='push_subscriptions')
    op.drop_table('push_subscriptions')
    op.drop_table('notification_settings')
    op.drop_index('ix_notifications_target', table_name='notifications')
    op.drop_index('ix_notifications_user_created', table_name='notifications')
    op.drop_table('notifications')
    op.drop_index('ix_outbox_processed_at', table_name='outbox')
    op.drop_table('outbox')
