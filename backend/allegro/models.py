"""Every table of every module, registered on one metadata (Alembic migrations and scripts import this)"""
from allegro.core.db import Base  # noqa: F401
from allegro.modules.accounts.models import AccessLink, User  # noqa: F401
from allegro.modules.catalog.models import (  # noqa: F401
    Collection, CollectionItem, MeasureSyncMarker, Opus, Performance, ScoreSyncMarker,
)
from allegro.modules.discussion.models import Comment, Reaction  # noqa: F401
from allegro.modules.publications.models import Material, Post, PostLink  # noqa: F401
from allegro.modules.site.models import Feedback, SitePage  # noqa: F401
