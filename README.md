# Allegro — альманах композиторов

Платформа, где звук, ноты и теоретическая беседа живут в одном окне: опусы с партитурой (PDF.js), синхронным плеером и рецензиями с таймкодами; личные кабинеты авторов; библиотека партитур с фильтрами; статьи и мастерская для разборов.

## Архитектура — распределённый монолит

```
                     [ Браузер ]
                         │
                 [ gateway: nginx :8080 ]
        ┌──────────┬─────┴──────┬────────────┬───────────┬──────────┐
        ▼          ▼            ▼            ▼           ▼          ▼
   [frontend]  [identity]   [catalog]    [content]  [discussion] [media]
   Nuxt 3 SSR  вход,        опусы,       статьи,    рецензии,    загрузки,
               профили      синхрониз.,  заметки,   таймкоды,    /media
                            сборники,    мастерская ветки
                            библиотека,
                            поиск
                   └──────────┴────────────┴───────────┴──────────┘
                                         │
                          [ PostgreSQL — одна общая БД ]      [ volume media ]
```

- У каждого сервиса свой `Dockerfile` (`backend/services/<name>/Dockerfile`), общий код — пакет `backend/allegro_common` (модели, БД, JWT, хранилище).
- Схема БД одна на всех, миграции — Alembic (`backend/migrations`), применяет одноразовый контейнер `migrate`.
- Файлы — локальное хранилище (`allegro_common/storage.py`); интерфейс готов к замене на S3/R2.

| Сервис | Маршруты |
|---|---|
| identity | `/api/auth/*`, `/api/users/*` |
| catalog | `/api/opuses*`, `/api/collections*`, `/api/library/facets`, `/api/search` |
| content | `/api/posts*` |
| discussion | `/api/comments*` |
| media | `/api/media`, `/media/*` |

### Партитуры: MusicXML с курсором и PDF

У опуса может быть один формат или оба сразу; слушатель переключается между ними, оба ведёт одна временная шкала.

- **MusicXML** (`.musicxml`, `.xml`, сжатый `.mxl` — экспорт MuseScore, Sibelius, Dorico, Finale) рендерится в браузере через OpenSheetMusicDisplay. Золотой бегунок идёт по нотам вслед за записью, клик по ноте перематывает запись, таймкоды в рецензиях переводят бегунок на нужный такт. Режим «Страницами» перелистывает лист там, где кончается печатная страница (разрывы страниц из файла), «Лентой» — плавная прокрутка.
- Синхронизация: по темпу из файла + «первая доля звучит на мм:сс». Для живого исполнения с агогикой — отметки тактов (`measure_sync_markers`): между ними бегунок интерполирует.
- **PDF** — печатная партитура; страницы перелистываются по отметкам (`score_sync_markers`). Если загружен и MusicXML, отметки строятся **автоматически** из его разрывов страниц (`allegro_common/musicxml.py`), иначе задаются вручную. Под страницей — бегунок прогресса по странице.
- Автор решает, можно ли скачивать ноты (`/api/opuses/{slug}/score`, `/api/opuses/{slug}/musicxml`).

Таблицы: `users`, `opuses`, `score_sync_markers` (страница N начинается на секунде T), `measure_sync_markers` (такт N начинается на секунде T), `collections` + `collection_items`, `posts` (`article` / `note` / `workshop`), `comments` (`parent_id` для веток, `timestamp_marker` для таймкода).

## Локальный запуск (без Docker)

Бэкенд — все сервисы в одном процессе на SQLite:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate                 # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt numpy  # numpy нужен только для демо-данных
alembic upgrade head
python -m scripts.seed                 # демо: 3 автора, 6 опусов с PDF и записями
python dev_server.py                   # http://127.0.0.1:8000/docs
```

Фронтенд:

```bash
cd frontend
npm install
npm run dev                            # http://localhost:3000
```

Демо-вход (вымышленные авторы из `scripts/seed.py`): `lev_orlovsky`, `kostya_theory`, `maria_viola`, пароль `allegro-demo`.

## Docker

```bash
docker compose up --build                                  # http://localhost:8080
docker compose run --rm migrate python -m scripts.seed     # демо-данные (по желанию)
```

## Тесты

```bash
cd backend
python -m pytest tests/test_platform.py
```

## Дизайн

Очень тёмный живописный фон (светотень, фактура холста), золочёные рамы, шрифты Playfair Display / Cormorant SC / EB Garamond, логотип — Tangerine. Вкладки и страницы партитуры перелистываются как листы книги.

## Устаревшее

Файлы прежнего одностраничного портфолио (`backend/app/`, `frontend/src/` и др.) не используются и исключены из репозитория через `.gitignore`. Остальные `.md` в корне, кроме этого README, описывают старую версию.
