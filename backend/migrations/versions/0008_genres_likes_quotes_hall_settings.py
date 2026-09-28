"""genres and instruments instead of ensemble/form/difficulty/tags; likes; quotes and links between posts;
hall settings; moderators

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-30
"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# A frozen copy of the vocabulary as it is today (a migration must not change when the code does)
INSTRUMENTS = {
    "фортепиано", "скрипка", "альт", "виолончель", "контрабас", "флейта", "гобой", "кларнет", "фагот",
    "саксофон", "валторна", "труба", "тромбон", "туба", "арфа", "гитара", "орган", "клавесин", "ударные",
    "челеста", "голос", "хор", "оркестр", "струнный оркестр", "баян", "аккордеон", "домра", "балалайка",
    "электроника", "солисты",
}
ALIASES = {
    "фортепьяно": "фортепиано", "ф-но": "фортепиано", "фп": "фортепиано", "рояль": "фортепиано", "piano": "фортепиано",
    "скр": "скрипка", "скр.": "скрипка", "violin": "скрипка", "вч": "виолончель", "вч.": "виолончель",
    "cello": "виолончель", "viola": "альт", "flute": "флейта", "вокал": "голос", "сопрано": "голос",
}
BY_COUNT = {1: "solo", 2: "duo", 3: "trio", 4: "quartet", 5: "quintet"}


def _norm(name: str) -> str:
    name = " ".join(str(name).strip().lower().replace("ё", "е").split())[:40]
    return ALIASES.get(name, name)


def _list(value) -> list:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return []
    return value if isinstance(value, list) else []


def _genre_and_instruments(ensemble, form, tags, instrumentation) -> tuple[str, list[str]]:
    instruments = [t for t in (_norm(t) for t in _list(tags)) if t in INSTRUMENTS]
    if not instruments and instrumentation:
        instruments = [_norm(i) for i in str(instrumentation).replace(";", ",").split(",") if i.strip()]
    if ensemble == "orchestra":
        return ("concerto" if instruments and instruments != ["оркестр"] else "orchestral"), instruments or ["оркестр"]
    if ensemble == "choir":
        return ("cantata" if form == "cantata" else "choir"), instruments or ["хор"]
    if form == "cantata":
        return "cantata", instruments
    if ensemble == "solo":
        return "solo", instruments
    if form == "sonata" and len(instruments) == 2 and "фортепиано" in instruments:
        return "duo_sonata", instruments
    return BY_COUNT.get(len(instruments), "ensemble" if ensemble == "chamber" else "other"), instruments


def upgrade() -> None:
    # ---- members: hall settings, moderators
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('hall', sa.JSON(), server_default=sa.text("'{}'"), nullable=False))
        batch_op.add_column(sa.Column('is_moderator', sa.Boolean(), server_default=sa.false(), nullable=False))

    # ---- works: one genre and a list of instruments
    with op.batch_alter_table('opuses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('genre', sa.String(length=20), server_default='other', nullable=False))
        batch_op.add_column(sa.Column('instruments', sa.JSON(), server_default=sa.text("'[]'"), nullable=False))
    bind = op.get_bind()
    # PostgreSQL won't put text into a JSON column without a cast; SQLite's CAST(… AS JSON) would make it 0
    value = "CAST(:instruments AS JSON)" if bind.dialect.name == "postgresql" else ":instruments"
    rows = bind.execute(sa.text("SELECT id, ensemble, form, tags, instrumentation FROM opuses")).all()
    for row in rows:
        genre, instruments = _genre_and_instruments(row.ensemble, row.form, row.tags, row.instrumentation)
        bind.execute(
            sa.text(f"UPDATE opuses SET genre = :genre, instruments = {value} WHERE id = :id"),
            {"genre": genre, "instruments": json.dumps(instruments, ensure_ascii=False), "id": row.id},
        )
    with op.batch_alter_table('opuses', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_opuses_genre'), ['genre'], unique=False)
        batch_op.drop_index(batch_op.f('ix_opuses_ensemble'))
        batch_op.drop_index(batch_op.f('ix_opuses_form'))
        batch_op.drop_column('ensemble')
        batch_op.drop_column('form')
        batch_op.drop_column('difficulty')
        batch_op.drop_column('tags')
        batch_op.drop_column('instrumentation')

    # ---- posts quoting posts
    with op.batch_alter_table('posts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('quote_post_id', sa.Uuid(), nullable=True))
        batch_op.create_index(batch_op.f('ix_posts_quote_post_id'), ['quote_post_id'], unique=False)
        batch_op.create_foreign_key('fk_posts_quote_post_id_posts', 'posts', ['quote_post_id'], ['id'], ondelete='SET NULL')

    # ---- links from a post's text to posts and works
    op.create_table(
        'post_links',
        sa.Column('post_id', sa.Uuid(), nullable=False),
        sa.Column('target_kind', sa.String(length=20), nullable=False),
        sa.Column('target_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('post_id', 'target_kind', 'target_id'),
    )
    op.create_index('ix_post_links_target', 'post_links', ['target_kind', 'target_id'], unique=False)

    # ---- likes
    op.create_table(
        'reactions',
        sa.Column('target_kind', sa.String(length=20), nullable=False),
        sa.Column('target_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('target_kind', 'target_id', 'user_id'),
    )
    op.create_index('ix_reactions_user_id', 'reactions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_reactions_user_id', table_name='reactions')
    op.drop_table('reactions')
    op.drop_index('ix_post_links_target', table_name='post_links')
    op.drop_table('post_links')
    with op.batch_alter_table('posts', schema=None) as batch_op:
        batch_op.drop_constraint('fk_posts_quote_post_id_posts', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_posts_quote_post_id'))
        batch_op.drop_column('quote_post_id')
    with op.batch_alter_table('opuses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('instrumentation', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('tags', sa.JSON(), server_default=sa.text("'[]'"), nullable=False))
        batch_op.add_column(sa.Column('difficulty', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('form', sa.String(length=20), server_default='other', nullable=False))
        batch_op.add_column(sa.Column('ensemble', sa.String(length=20), server_default='chamber', nullable=False))
        batch_op.create_index(batch_op.f('ix_opuses_form'), ['form'], unique=False)
        batch_op.create_index(batch_op.f('ix_opuses_ensemble'), ['ensemble'], unique=False)
        batch_op.drop_index(batch_op.f('ix_opuses_genre'))
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE opuses SET tags = instruments, ensemble = CASE WHEN genre = 'solo' THEN 'solo' "
                         "WHEN genre IN ('symphony', 'orchestral', 'concerto') THEN 'orchestra' "
                         "WHEN genre IN ('choir', 'cantata') THEN 'choir' ELSE 'chamber' END"))
    with op.batch_alter_table('opuses', schema=None) as batch_op:
        batch_op.drop_column('instruments')
        batch_op.drop_column('genre')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_moderator')
        batch_op.drop_column('hall')
