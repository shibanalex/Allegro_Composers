# One-shot job: applies Alembic migrations to the shared database (and can seed demo data).
# Build context is backend/.
#   docker compose run --rm migrate python -m scripts.seed
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt numpy  # numpy: demo audio synthesis in scripts/seed.py

COPY allegro_common ./allegro_common
COPY alembic.ini .
COPY migrations ./migrations
COPY scripts ./scripts

CMD ["alembic", "upgrade", "head"]
