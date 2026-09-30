# Разработка

## Запуск локально

Бэкенд (Python 3.12+):

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Linux/macOS: .venv/bin/python
cp .env.example .env        # и впишите SECRET_KEY: python -c "import secrets; print(secrets.token_urlsafe(48))"
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m allegro          # the same as: python -m uvicorn allegro.main:app --port 8000 (add --reload to restart on saves)
```

Локально база — `backend/allegro_platform.db` (SQLite), файлы — `backend/media/`.

Фронтенд (Node 24):

```bash
cd frontend
npm ci
npx nuxi dev --port 3000     # http://localhost:3000, /api и /media проксируются на :8000
```

Первый аккаунт: задайте `SETUP_TOKEN` в `backend/.env` и откройте `/setup` — или используйте
существующую базу. Демо-наполнение (вымышленные авторы, по умолчанию «в тени»):
`python -m scripts.seed` (нужны `requirements-tools.txt`).

Как в продакшене (PostgreSQL + MinIO вместо Yandex Object Storage, один контейнер сайта):

```bash
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))") docker compose up --build
```

## Тесты

```bash
cd backend
.venv/Scripts/python -m pytest                       # все тесты, на SQLite
MIGRATION_TEST_URL=postgresql://user:pass@localhost:5432/db \
  .venv/Scripts/python -m pytest tests/test_migrations.py   # миграции на PostgreSQL
```

- `test_platform.py` — сочинения, партитуры, посты, комментарии, поиск, безопасность файлов.
- `test_community.py` — роли, регистрация, сброс пароля, администрирование, исполнения,
  выставка, «О нас», предложения, ограничения частоты.
- `test_architecture.py` — границы модулей (см. ARCHITECTURE.md).
- `test_migrations.py` — миграции сохраняют данные.

## Скрипты (`backend/scripts`)

| Команда | Что делает |
|---|---|
| `python -m scripts.shadow list \| hide \| show <имена>` | «тень»: скрыть/вернуть аккаунт со всем опубликованным |
| `python -m scripts.set_password <имя>` | задать пароль (вводится скрыто) |
| `python -m scripts.import_telegram "<папка выгрузки>" --user <имя>` | импорт канала Telegram в блог |
| `python -m scripts.seed [--visible]` | демо-авторы (вымышленные) |

## Как добавить…

- **Поле в таблицу:** модель → `alembic revision --autogenerate -m "…"` → проверить миграцию
  (на SQLite удаление/изменение колонок идёт через пересоздание таблицы) → тест.
- **Эндпоинт:** схема в `schemas.py` → сценарий в `service.py` (правила, права, `db.commit()`) →
  тонкий маршрут в `api.py`.
- **Модуль:** см. конец раздела 3 в ARCHITECTURE.md.

## Стиль

- Комментарии объясняют «почему», а не «что».
- Сервисы бросают ошибки из `core/errors.py`, а не `HTTPException`.
- Побочные эффекты после сохранения — через `after_commit`.
- Тексты для людей — по-русски; код и комментарии — по-английски.
