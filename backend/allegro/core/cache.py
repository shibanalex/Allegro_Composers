"""A small key-value cache: Redis when REDIS_URL is set, otherwise the server's own memory.

Used for what many pages read and few requests change (the last comments under each post of the feed).
Values are JSON. The cache is only a shortcut: every value can be rebuilt from the database, so a Redis
that is down or wiped costs a few queries, never data — errors are logged and the caller falls back.
"""
import json
import logging
import time
from threading import Lock
from typing import Any, Iterable, Optional

from allegro.core.config import settings

log = logging.getLogger("allegro.cache")
PREFIX = "allegro:"


class MemoryCache:
    """One process, a bounded number of keys, expiry on read"""

    def __init__(self, max_keys: int = 5000):
        self._data: dict[str, tuple[float, str]] = {}
        self._lock = Lock()
        self.max_keys = max_keys

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        now, found = time.monotonic(), {}
        with self._lock:
            for key in keys:
                item = self._data.get(key)
                if item and item[0] > now:
                    found[key] = json.loads(item[1])
                elif item:
                    del self._data[key]
        return found

    def set_many(self, values: dict[str, Any], ttl: int) -> None:
        expires = time.monotonic() + ttl
        with self._lock:
            if len(self._data) + len(values) > self.max_keys:
                self._data.clear()  # crude, but the cache is only a shortcut
            for key, value in values.items():
                self._data[key] = (expires, json.dumps(value, ensure_ascii=False, default=str))

    def delete(self, keys: Iterable[str]) -> None:
        with self._lock:
            for key in keys:
                self._data.pop(key, None)


class RedisCache:
    def __init__(self, url: str):
        import redis

        self.client = redis.Redis.from_url(url, socket_timeout=0.5, socket_connect_timeout=0.5)

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        if not keys:
            return {}
        try:
            values = self.client.mget([PREFIX + k for k in keys])
        except Exception as e:  # a cache that doesn't answer is a cache miss
            log.warning("redis get: %s", e)
            return {}
        return {k: json.loads(v) for k, v in zip(keys, values) if v is not None}

    def set_many(self, values: dict[str, Any], ttl: int) -> None:
        if not values:
            return
        try:
            with self.client.pipeline() as pipe:
                for key, value in values.items():
                    pipe.set(PREFIX + key, json.dumps(value, ensure_ascii=False, default=str), ex=ttl)
                pipe.execute()
        except Exception as e:
            log.warning("redis set: %s", e)

    def delete(self, keys: Iterable[str]) -> None:
        keys = [PREFIX + k for k in keys]
        if not keys:
            return
        try:
            self.client.delete(*keys)
        except Exception as e:
            log.warning("redis delete: %s", e)


def _make_cache():
    return RedisCache(settings.redis_url) if settings.redis_url else MemoryCache()


cache: Any = _make_cache()


def cached_many(keys: dict[Any, str], load, ttl: int) -> dict[Any, Any]:
    """Values for several ids: from the cache, and the missing ones from `load(missing_ids)` (then cached)"""
    hits = cache.get_many(list(keys.values()))
    found = {i: hits[k] for i, k in keys.items() if k in hits}
    missing = [i for i in keys if i not in found]
    if missing:
        loaded = load(missing)
        cache.set_many({keys[i]: loaded.get(i) for i in missing}, ttl)
        found.update({i: loaded.get(i) for i in missing})
    return found


def forget(keys: Optional[Iterable[str]]) -> None:
    cache.delete(list(keys or []))
