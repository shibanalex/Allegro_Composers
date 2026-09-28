"""Who a member is and what that lets them publish.

The role is the member's own choice (at registration or later in their hall) and mostly shapes their
hall; everyone can keep a blog, comment and share materials. A few kinds of publications need a role:

    composer   — works (opuses), articles
    theorist   — articles and reviews (musicologists)
    performer  — performances
    listener   — blog and comments only

Administrators (the site's owners) additionally publish news and manage invitations and feedback.
"""
from enum import StrEnum


class Role(StrEnum):
    COMPOSER = "composer"
    THEORIST = "theorist"
    PERFORMER = "performer"
    LISTENER = "listener"


ROLE_LABELS = {
    Role.COMPOSER: "Композитор",
    Role.THEORIST: "Теоретик / музыковед",
    Role.PERFORMER: "Исполнитель",
    Role.LISTENER: "Слушатель",
}


class Capability(StrEnum):
    PUBLISH_OPUS = "publish_opus"
    PUBLISH_ARTICLE = "publish_article"
    PUBLISH_PERFORMANCE = "publish_performance"
    PUBLISH_NEWS = "publish_news"
    MANAGE_SITE = "manage_site"


CAPABILITIES: dict[Role, frozenset[Capability]] = {
    Role.COMPOSER: frozenset({Capability.PUBLISH_OPUS, Capability.PUBLISH_ARTICLE}),
    Role.THEORIST: frozenset({Capability.PUBLISH_ARTICLE}),
    Role.PERFORMER: frozenset({Capability.PUBLISH_PERFORMANCE}),
    Role.LISTENER: frozenset(),
}

# Administrators publish the site's news and run it, on top of what their own role allows
ADMIN_CAPABILITIES = frozenset({Capability.PUBLISH_NEWS, Capability.MANAGE_SITE})

CAPABILITY_REFUSALS = {
    Capability.PUBLISH_OPUS: "Публиковать сочинения могут композиторы — роль меняется в «Оформить зал»",
    Capability.PUBLISH_ARTICLE: "Статьи пишут композиторы и теоретики — роль меняется в «Оформить зал»",
    Capability.PUBLISH_PERFORMANCE: "Исполнения публикуют исполнители — роль меняется в «Оформить зал»",
    Capability.PUBLISH_NEWS: "Новости публикуют администраторы",
    Capability.MANAGE_SITE: "Только для администраторов",
}

# Styles of a hall: the era its owner feels closest to
HALL_THEMES = {
    "baroque": "Барокко и классицизм",
    "romantic": "Романтизм",
    "modern": "Модерн",
    "avantgarde": "Авангард",
}
DEFAULT_HALL_THEME = "romantic"


def capabilities_of(role: str, is_admin: bool) -> frozenset[Capability]:
    try:
        own = CAPABILITIES[Role(role)]
    except ValueError:
        own = frozenset()
    return own | ADMIN_CAPABILITIES if is_admin else own


def can(user, capability: Capability) -> bool:
    return capability in capabilities_of(user.role, user.is_admin)
