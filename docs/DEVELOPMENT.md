# Development

## Local Setup

Backend (uses SQLite at `backend/allegro_platform.db` and `backend/media/`):

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# Generate SECRET_KEY (>= 32 chars):
# python3 -c "import secrets; print(secrets.token_urlsafe(48))"
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m allegro --reload
```

Frontend (Node 24+, proxies `/api` and `/media` to `:8000`):

```bash
cd frontend
npm ci
npx nuxi dev --port 3000
```

Optional real-time chat daemon (Centrifugo on `:8001`; without it the client
falls back to periodic polling):

```bash
cd backend
eval "$(.venv/bin/python -m allegro.core.realtime)"
CENTRIFUGO_CLIENT_ALLOWED_ORIGINS=http://localhost:3000 centrifugo --config ../deploy/centrifugo.json
```

## Tests

```bash
cd backend
.venv/bin/python -m pytest
```

To test Alembic migrations against PostgreSQL:

```bash
MIGRATION_TEST_URL=postgresql://user:pass@localhost:5432/db \
  .venv/bin/python -m pytest tests/test_migrations.py
```

## CLI Utilities (`backend/scripts`)

| Command | Purpose |
|---|---|
| `python -m scripts.shadow list \| hide \| show <handles>` | Hide or restore a member and all their publications |
| `python -m scripts.set_password <handle>` | Set a member password interactively |
| `python -m scripts.import_telegram "<export_dir>" --user <handle>` | Import a Telegram channel export into a hall blog |
| `python -m scripts.seed [--visible]` | Populate demo composer halls and opuses |

## Conventions

- Domain services raise `core.errors` exceptions, never `HTTPException`.
- Side effects after persistence go through `after_commit`.
- Code, docstrings, and comments stay in English; user-facing UI strings are Russian.
