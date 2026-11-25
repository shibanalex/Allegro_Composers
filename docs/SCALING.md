# Performance and Scaling

Current bottlenecks are network latency between separate hosting regions rather
than application code. The platform runs as a single container with optional
external state:

- **Connection pooling:** `core/db.py` disables server-side prepared statements
  to stay compatible with PgBouncer (`-pooler` connection URLs).
- **Indexes and assets:** Feed queries use composite `(author, status,
  created_at)` indexes; uploaded images generate `<= 800 px` WebP thumbnails in
  `core/images.py` off the event loop so feed pages avoid full-resolution image
  payloads.
- **Caching (`core/cache.py`):** Comment previews cache in Redis (`MGET`) when
  `REDIS_URL` is configured and degrade cleanly to in-process memory if Redis is
  unavailable.
- **Rate limiting (`core/ratelimit.py`):** Uses Redis when horizontal scaling
  adds multiple API workers, or local memory for single-node deployments.
- **Real-time (`core/realtime.py`):** Chat fanout runs through Centrifugo and
  degrades to polling if the WebSocket process is unreachable.
