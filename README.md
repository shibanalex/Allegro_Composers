# Allegro

![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776ab?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-Modular%20Monolith-009688?style=flat-square)
![Nuxt 3](https://img.shields.io/badge/Nuxt%203-Vue%203%20%2F%20TS-00dc82?style=flat-square)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-SQLAlchemy%202.0-336791?style=flat-square)

A full-stack platform for classical composers, theorists, and performers.
Members publish scores (MusicXML and PDF) synchronized with audio playback,
audio waveforms, performer recordings, essays, and real-time discussions
inside customizable personal halls.

## Architecture

The backend (`backend/allegro`) is a modular monolith behind a single Caddy
reverse proxy (`deploy/Caddyfile`). Domain boundaries are enforced
automatically by `backend/tests/test_architecture.py`.

```
Browser -> Caddy (:PORT)
             |-- /connection/** -> Centrifugo (:8001, WebSocket fanout)
             '-- /*             -> Nuxt 3 SSR (:3001)
                                      '-- /api/** -> FastAPI (:8000)
                                                       |-- PostgreSQL
                                                       '-- S3 / local media
```

Modules only communicate in a strict DAG through each module's public
`service.py` / `schemas.py` / `deps.py` surface:

```
core (db, security, storage, images, peaks, ratelimit, realtime)
  <- accounts <- discussion <- catalog <- publications <- media <- site <- feed <- notifications <- search
```

Cross-cutting design choices:

- **Transactional side effects:** Storage deletions and notification fanout
  register callbacks via `after_commit(db, fn)` in `core/db.py` so rollbacks
  never orphan database pointers.
- **Score and audio sync:** Uploaded MusicXML/MXL archives undergo zip-bomb and
  XXE checks; `ffmpeg` extracts volume peaks for client waveform rendering.
- **Security:** `scrypt` password hashing, `HttpOnly` JWT cookies paired with
  `Sec-Fetch-Site` / `Origin` CSRF validation, encrypted optional email storage,
  and per-member daily upload quotas.
- **Live fallback:** Community chat pushes updates via Centrifugo and drops back
  to HTTP polling automatically if the socket daemon is absent.

Further details are split into [ARCHITECTURE.md](docs/ARCHITECTURE.md),
[DEVELOPMENT.md](docs/DEVELOPMENT.md), [DEPLOYMENT.md](docs/DEPLOYMENT.md), and
[SECURITY.md](docs/SECURITY.md).

## Running Locally

Full containerized stack (Caddy, Nuxt, FastAPI, PostgreSQL, MinIO):

```bash
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))") \
  docker compose up --build
```

Lightweight local backend and frontend (uses SQLite and `backend/media/`):

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m allegro
```

```bash
cd frontend
npm ci
npx nuxi dev --port 3000
```

## Tests

```bash
cd backend
.venv/bin/python -m pytest
```
