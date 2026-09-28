"""roles, invitations, encrypted e-mail, performances, showcase, site pages and feedback

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-29

- users: role, hall_theme, is_admin, invited_by_id; the e-mail becomes optional and is kept only
  encrypted (+ a keyed hash for lookups); existing members become composers, the oldest visible
  member becomes an administrator (the site's owner)
- access_links: one-time invitation and password-reset links (only their hashes are stored)
- opuses.featured: works on the composer's showcase
- performances, site_pages, feedback: new tables
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from allegro.core.security import decrypt_email, email_index, encrypt_email

revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('role', sa.String(length=20), server_default='listener', nullable=False))
        batch_op.add_column(sa.Column('hall_theme', sa.String(length=20), server_default='romantic', nullable=False))
        batch_op.add_column(sa.Column('is_admin', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column('invited_by_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('email_hash', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('email_encrypted', sa.Text(), nullable=True))
        batch_op.create_index(batch_op.f('ix_users_role'), ['role'], unique=False)
        batch_op.create_index(batch_op.f('ix_users_email_hash'), ['email_hash'], unique=True)
        batch_op.create_foreign_key('fk_users_invited_by', 'users', ['invited_by_id'], ['id'], ondelete='SET NULL')

    # Existing members: composers; e-mail moves into the encrypted columns; the owner becomes an administrator
    bind = op.get_bind()
    users = sa.table(
        'users', sa.column('id', sa.Uuid()), sa.column('email', sa.String()), sa.column('role', sa.String()),
        sa.column('is_admin', sa.Boolean()), sa.column('is_hidden', sa.Boolean()), sa.column('created_at', sa.DateTime()),
        sa.column('email_hash', sa.String()), sa.column('email_encrypted', sa.Text()),
    )
    rows = bind.execute(sa.select(users.c.id, users.c.email)).all()
    for user_id, email in rows:
        values = {'role': 'composer'}
        if email:
            values.update(email_hash=email_index(email), email_encrypted=encrypt_email(email))
        bind.execute(users.update().where(users.c.id == user_id).values(**values))
    owner = bind.execute(
        sa.select(users.c.id).where(users.c.is_hidden == sa.false()).order_by(users.c.created_at).limit(1)
    ).scalar()
    if owner:
        bind.execute(users.update().where(users.c.id == owner).values(is_admin=True))

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('ix_users_email')
        batch_op.drop_column('email')

    with op.batch_alter_table('opuses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('featured', sa.Boolean(), server_default=sa.false(), nullable=False))

    op.create_table(
        'access_links',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('purpose', sa.String(length=20), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('note', sa.String(length=200), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=True),
        sa.Column('target_user_id', sa.Uuid(), nullable=True),
        sa.Column('used_by_id', sa.Uuid(), nullable=True),
        sa.Column('created_by_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['used_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_access_links_purpose'), 'access_links', ['purpose'], unique=False)
    op.create_index(op.f('ix_access_links_token_hash'), 'access_links', ['token_hash'], unique=True)

    op.create_table(
        'performances',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('performer_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('composer_name', sa.String(length=160), nullable=True),
        sa.Column('opus_id', sa.Uuid(), nullable=True),
        sa.Column('description_md', sa.Text(), nullable=True),
        sa.Column('audio_type', sa.String(length=20), nullable=False),
        sa.Column('audio_source', sa.String(length=512), nullable=False),
        sa.Column('audio_duration_seconds', sa.Float(), nullable=True),
        sa.Column('recorded_year', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('play_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['performer_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['opus_id'], ['opuses.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_performances_performer_id'), 'performances', ['performer_id'], unique=False)
    op.create_index(op.f('ix_performances_opus_id'), 'performances', ['opus_id'], unique=False)
    op.create_index(op.f('ix_performances_status'), 'performances', ['status'], unique=False)
    op.create_index(op.f('ix_performances_created_at'), 'performances', ['created_at'], unique=False)

    op.create_table(
        'site_pages',
        sa.Column('slug', sa.String(length=40), nullable=False),
        sa.Column('content_md', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_by_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('slug'),
    )

    op.create_table(
        'feedback',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('author_id', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='new', nullable=False),
        sa.Column('reply_md', sa.Text(), nullable=True),
        sa.Column('replied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_feedback_author_id'), 'feedback', ['author_id'], unique=False)
    op.create_index(op.f('ix_feedback_status'), 'feedback', ['status'], unique=False)
    op.create_index(op.f('ix_feedback_created_at'), 'feedback', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('feedback')
    op.drop_table('site_pages')
    op.drop_table('performances')
    op.drop_table('access_links')
    with op.batch_alter_table('opuses', schema=None) as batch_op:
        batch_op.drop_column('featured')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=255), nullable=True))
    bind = op.get_bind()
    users = sa.table('users', sa.column('id', sa.Uuid()), sa.column('username', sa.String()),
                     sa.column('email', sa.String()), sa.column('email_encrypted', sa.Text()))
    for user_id, username, encrypted in bind.execute(sa.select(users.c.id, users.c.username, users.c.email_encrypted)).all():
        # the old schema required an address: members who never gave one get a placeholder
        email = decrypt_email(encrypted) or f"{username}@users.invalid"
        bind.execute(users.update().where(users.c.id == user_id).values(email=email))
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('email', nullable=False)
        batch_op.create_index('ix_users_email', ['email'], unique=True)
        batch_op.drop_constraint('fk_users_invited_by', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_users_email_hash'))
        batch_op.drop_index(batch_op.f('ix_users_role'))
        for column in ('email_encrypted', 'email_hash', 'invited_by_id', 'is_admin', 'hall_theme', 'role'):
            batch_op.drop_column(column)
