# Architecture

Allegro is structured as a modular monolith (`backend/allegro`) behind a Caddy
reverse proxy (`deploy/Caddyfile`). Module import boundaries are verified in CI
by `backend/tests/test_architecture.py`.

## Container Topology

```
Browser -> Caddy (:PORT)
             |-- /connection/** -> Centrifugo (:8001)
             '-- /*             -> Nuxt 3 SSR (:3001)
                                      '-- /api/** -> FastAPI (:8000)
                                                       |-- PostgreSQL
                                                       '-- Object Storage (S3 / local)
```

Caddy is the only externally exposed process. Media files are uploaded through
FastAPI (for type validation and daily quota accounting) and served directly
from S3-compatible object storage in production.

## Module Layering

Each domain module under `backend/allegro/modules/` keeps strict internal
layers:

| File | Responsibility | Forbidden |
|---|---|---|
| `api.py` | HTTP parsing, dependency injection, response serialization | Business rules |
| `service.py` | Use cases, authorization checks, single `db.commit()` | HTTP framework imports |
| `repository.py` | Parameterized SQLAlchemy queries | Calling `commit()` |
| `models.py` | Module-owned tables | Cross-module table ownership |
| `schemas.py` | Pydantic request and response contracts | Persistence logic |

Cross-module dependencies follow one direction only:

```
core
  <- accounts <- discussion <- catalog <- publications <- media <- site <- feed <- notifications <- search
```

Reverse wiring (such as registering comment targets from `catalog` and
`publications` in `discussion`, or profile counters in `accounts`) happens once
at startup in `backend/allegro/main.py`.

## Cross-Cutting Mechanisms

- **Transactions:** Every use case executes within one SQLAlchemy transaction.
  Side effects that must only run after durable commit (such as deleting
  replaced media objects or publishing to Centrifugo) use `after_commit(db, fn)`
  in `core/db.py`.
- **Errors:** Domain services raise typed errors (`NotFound`, `Forbidden`,
  `Invalid`, `Conflict`, `TooManyAttempts`) from `core/errors.py`, mapped to
  consistent `{"detail": ..., "code": ...}` responses.
- **Caching:** Recent discussion comments and feed snippets optionally cache in
  Redis (`REDIS_URL`) via `core/cache.py` and fall back transparently to
  in-process memory or direct database queries.
