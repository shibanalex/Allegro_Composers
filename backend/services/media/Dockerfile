# media service — build context is backend/ (docker compose build media)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY allegro_common ./allegro_common
COPY services/__init__.py ./services/__init__.py
COPY services/media ./services/media

EXPOSE 8000
CMD ["uvicorn", "services.media.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
