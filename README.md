# Allegro

Сообщество композиторов, теоретиков, исполнителей и слушателей.

- **Композиторы** выставляют сочинения: партитуры (PDF и интерактивный MusicXML с курсором),
  записи, синхронизация страниц и тактов с записью; «Выставка» избранного и «Библиотека» с фильтрами.
- **Теоретики** пишут статьи и обзоры, **исполнители** делятся исполнениями, **все** ведут блоги
  (как канал в Telegram), комментируют с таймкодами и собирают материалы.
- У каждого — свой **зал** (`/@имя`) в стиле одной из эпох: барокко и классицизм, романтизм,
  модерн, авангард.
- Регистрация открыта всем; почта необязательна и хранится зашифрованной.

Сайт: https://allegro-9dz4.onrender.com

## Устройство

Модульный монолит на FastAPI (`backend/allegro`) + Nuxt 3 (`frontend`), PostgreSQL, S3-хранилище;
в продакшене — один контейнер на Render.

| Документ | О чём |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | модули, границы, слои, роли, решения |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | запуск локально, тесты, скрипты |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Render, Neon, Yandex Object Storage, домен |
| [docs/SECURITY.md](docs/SECURITY.md) | что защищено и как |
| [docs/SCALING.md](docs/SCALING.md) | производительность; когда нужны Redis, очереди, WebSocket |

## Быстрый старт

```bash
cd backend && python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
cp .env.example .env   # впишите SECRET_KEY
.venv/Scripts/python -m alembic upgrade head && .venv/Scripts/python -m allegro
cd ../frontend && npm ci && npx nuxi dev --port 3000
```
