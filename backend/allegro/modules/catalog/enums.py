"""Controlled vocabularies of the catalog with Russian labels (the frontend mirrors them in utils/labels.ts)"""

ENSEMBLES = {
    "solo": "Соло",
    "chamber": "Камерный ансамбль",
    "orchestra": "Симфонический оркестр",
    "choir": "Хор",
}

FORMS = {
    "sonata": "Соната",
    "suite": "Сюита",
    "miniature": "Миниатюра",
    "variations": "Вариации",
    "cantata": "Кантата",
    "other": "Другое",
}

DIFFICULTY = {1: "Начальная", 2: "Лёгкая", 3: "Средняя", 4: "Сложная", 5: "Виртуозная"}

AUDIO_TYPES = ("none", "youtube", "hosted_file")

# Who may download the score PDF
SCORE_ACCESS = {
    "free": "Свободное скачивание",
    "view_only": "Только просмотр",
    "paid": "За донат (скоро)",
}

STATUSES = ("published", "draft", "unlisted")
