"""Controlled vocabularies of the catalog with Russian labels (the frontend mirrors them in utils/labels.ts)"""

# What a work is written for: one choice instead of «состав», «форма», «сложность» and tags.
# Each genre suggests its usual instruments; the composer keeps them or edits the list (Opus.instruments).
# The frontend mirrors this table in utils/labels.ts.
GENRES: dict[str, tuple[str, list[str]]] = {
    "solo": ("Соло", ["фортепиано"]),
    "duo_sonata": ("Соната для инструмента и фортепиано", ["скрипка", "фортепиано"]),
    "duo": ("Дуэт", []),
    "trio": ("Трио", ["скрипка", "виолончель", "фортепиано"]),
    "quartet": ("Квартет", ["скрипка", "скрипка", "альт", "виолончель"]),
    "quintet": ("Квинтет", ["фортепиано", "скрипка", "скрипка", "альт", "виолончель"]),
    "ensemble": ("Камерный ансамбль", []),
    "concerto": ("Концерт", ["фортепиано", "оркестр"]),
    "symphony": ("Симфония", ["оркестр"]),
    "orchestral": ("Оркестровая пьеса", ["оркестр"]),
    "vocal": ("Романс, песня", ["голос", "фортепиано"]),
    "choir": ("Хор", ["хор"]),
    "cantata": ("Кантата, оратория, опера", ["солисты", "хор", "оркестр"]),
    "other": ("Другое", []),
}
GENRE_LABELS = {k: label for k, (label, _) in GENRES.items()}

# One name per instrument, so the catalogue can filter by it («фортепьяно», «ф-но» → «фортепиано»)
INSTRUMENT_ALIASES = {
    "фортепьяно": "фортепиано", "ф-но": "фортепиано", "фп": "фортепиано", "рояль": "фортепиано", "piano": "фортепиано",
    "скр": "скрипка", "скр.": "скрипка", "violin": "скрипка", "вч": "виолончель", "вч.": "виолончель",
    "виолончели": "виолончель", "cello": "виолончель", "viola": "альт", "flute": "флейта", "вокал": "голос",
    "сопрано": "голос", "меццо-сопрано": "голос", "тенор": "голос", "баритон": "голос", "бас": "голос",
}
MAX_INSTRUMENTS = 30


def normalize_instrument(name: str) -> str:
    name = " ".join(name.strip().lower().replace("ё", "е").split())[:40]
    return INSTRUMENT_ALIASES.get(name, name)

AUDIO_TYPES = ("none", "youtube", "hosted_file")

# Who may download the score PDF
SCORE_ACCESS = {
    "free": "Свободное скачивание",
    "view_only": "Только просмотр",
    "paid": "За донат (скоро)",
}

STATUSES = ("published", "draft", "unlisted")
