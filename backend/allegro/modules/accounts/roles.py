"""Role-based access: who a member is and what that lets them do.

Every action that changes something is a *capability*. A member's capabilities are the union of:

- what every member may do (comment, like, keep a blog, share materials);
- what their musical role adds; the role is the member's own choice, at registration or later:

      composer  ; works (opuses), sketches, articles
      theorist  ; articles and reviews (musicologists)
      performer ; performances
      listener  ; nothing more: listens, reads, discusses

- what their staff level adds; given by an administrator:

      moderator     ; removes other people's comments and posts
      administrator ; also news, invitations, the site's pages, feedback answers, members' rights

The table lives in code, not in the database: it changes with the features themselves, is checked by
the tests and costs nothing at run time. The API checks it with `require(Capability.X)` (accounts.deps)
or `can(user, Capability.X)` in services; the site shows or hides buttons with `useAuth().can('x')`.
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
    # every member
    COMMENT = "comment"
    CHAT = "chat"
    REACT = "react"
    PUBLISH_NOTE = "publish_note"  # a blog post
    SHARE_MATERIAL = "share_material"
    # by musical role
    PUBLISH_OPUS = "publish_opus"
    PUBLISH_ARTICLE = "publish_article"
    PUBLISH_PERFORMANCE = "publish_performance"
    PUBLISH_SKETCH = "publish_sketch"  # a quick voice note or improvisation
    # staff
    MODERATE = "moderate"
    PUBLISH_NEWS = "publish_news"
    MANAGE_SITE = "manage_site"


EVERY_MEMBER = frozenset({Capability.COMMENT, Capability.CHAT, Capability.REACT, Capability.PUBLISH_NOTE, Capability.SHARE_MATERIAL})

CAPABILITIES: dict[Role, frozenset[Capability]] = {
    Role.COMPOSER: EVERY_MEMBER | {Capability.PUBLISH_OPUS, Capability.PUBLISH_ARTICLE, Capability.PUBLISH_SKETCH},
    Role.THEORIST: EVERY_MEMBER | {Capability.PUBLISH_ARTICLE},
    Role.PERFORMER: EVERY_MEMBER | {Capability.PUBLISH_PERFORMANCE},
    Role.LISTENER: EVERY_MEMBER,
}

MODERATOR_CAPABILITIES = frozenset({Capability.MODERATE})
ADMIN_CAPABILITIES = MODERATOR_CAPABILITIES | {
    Capability.PUBLISH_NEWS, Capability.MANAGE_SITE,
}

CAPABILITY_LABELS = {
    Capability.COMMENT: "Комментировать",
    Capability.CHAT: "Писать в чат",
    Capability.REACT: "Отмечать «нравится»",
    Capability.PUBLISH_NOTE: "Вести блог",
    Capability.SHARE_MATERIAL: "Делиться материалами",
    Capability.PUBLISH_OPUS: "Публиковать сочинения",
    Capability.PUBLISH_ARTICLE: "Писать статьи и обзоры",
    Capability.PUBLISH_PERFORMANCE: "Публиковать исполнения",
    Capability.PUBLISH_SKETCH: "Выкладывать эскизы",
    Capability.MODERATE: "Модерировать",
    Capability.PUBLISH_NEWS: "Публиковать новости",
    Capability.MANAGE_SITE: "Управлять сайтом",
}

CAPABILITY_REFUSALS = {
    Capability.COMMENT: "Комментирование для вас закрыто",
    Capability.CHAT: "Чат для вас закрыт",
    Capability.REACT: "Отметки для вас закрыты",
    Capability.PUBLISH_NOTE: "Блог для вас закрыт",
    Capability.SHARE_MATERIAL: "Материалы для вас закрыты",
    Capability.PUBLISH_OPUS: "Публиковать сочинения могут композиторы — роль меняется в «Оформить зал»",
    Capability.PUBLISH_ARTICLE: "Статьи пишут композиторы и теоретики — роль меняется в «Оформить зал»",
    Capability.PUBLISH_PERFORMANCE: "Исполнения публикуют исполнители — роль меняется в «Оформить зал»",
    Capability.PUBLISH_SKETCH: "Эскизы выкладывают композиторы — роль меняется в «Оформить зал»",
    Capability.MODERATE: "Только для модераторов",
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


def capabilities_of(role: str, is_admin: bool, is_moderator: bool = False) -> frozenset[Capability]:
    try:
        own = CAPABILITIES[Role(role)]
    except ValueError:
        own = EVERY_MEMBER
    if is_admin:
        return own | ADMIN_CAPABILITIES
    if is_moderator:
        return own | MODERATOR_CAPABILITIES
    return own


def user_capabilities(user) -> frozenset[Capability]:
    return capabilities_of(user.role, user.is_admin, getattr(user, "is_moderator", False))


def can(user, capability: Capability) -> bool:
    return capability in user_capabilities(user)


def matrix() -> list[dict]:
    """The whole table, for the administrator's page and «О нас»"""
    columns = {**{r.value: CAPABILITIES[r] for r in Role}, "moderator": EVERY_MEMBER | MODERATOR_CAPABILITIES,
               "admin": EVERY_MEMBER | ADMIN_CAPABILITIES}
    return [{"capability": c.value, "label": CAPABILITY_LABELS[c], "who": [k for k, caps in columns.items() if c in caps]}
            for c in Capability]
