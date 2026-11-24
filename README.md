# Allegro — Classical Music Collaboration & Interactive Score Platform

**Allegro** is a full-stack community platform for classical composers, music theorists, performers, and listeners. Built as a modular monolith in **FastAPI** (`backend/allegro`) + **Nuxt 3 / Vue 3** (`frontend`), backed by **PostgreSQL**, **S3-compatible object storage**, and real-time **Centrifugo** WebSockets.

## Key Capabilities

- **Interactive Score & Audio Sync:** Upload PDF and interactive **MusicXML** scores with live playback cursor synchronization across measures and pages, waveform audio player (`ffmpeg` server-side generation), and timestamped measure/timecode discussions.
- **Composer Halls (`/@handle`):** Personal customizable halls styled after classical eras (*Baroque & Classicism*, *Romanticism*, *Modernism*, *Avant-garde*), featuring curated exhibitions, full opus libraries, and composer blogs.
- **Real-Time Community:** Live WebSocket community chat (`Centrifugo`), performer recordings linked to scores, and encrypted optional email storage.

## Architecture & Documentation

| Document | Scope |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Modular boundaries (`accounts`, `catalog`, `publications`, `discussion`, `feed`, `media`, `site`), layers & design decisions |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Local setup, Alembic migrations, pytest suite, utility scripts |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Docker, PostgreSQL, S3 object storage, reverse-proxy setup |
| [docs/SECURITY.md](docs/SECURITY.md) | JWT/HMAC derivation, encrypted PII, rate limiting, strict `ffmpeg` & upload validation |

## Tech Stack

`Python` · `FastAPI` · `SQLAlchemy 2.0` · `Alembic` · `PostgreSQL` · `Nuxt 3` · `Vue 3` · `TypeScript` · `Tailwind CSS` · `Centrifugo WebSockets` · `S3` · `Docker` · `pytest`
