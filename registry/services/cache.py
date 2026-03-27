# SkillPM Registry - In-Memory Cache Service (Phase 2)
# Author: Bogdan Ticu
# License: MIT
#
# Simple in-memory cache with TTL support. Used for caching
# frequently accessed data like skill listings, search results,
# and analytics computations.
#
# For production, replace with Redis or memcached.

import time
import hashlib
import json
from typing import Any, Optional, Callable
from functools import wraps
from threading import Lock


class CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.expires_at = time.time() + ttl_seconds


class InMemoryCache:
    """Thread-safe in-memory cache with TTL."""

    def __init__(self, default_ttl: int = 60, max_entries: int = 1000):
        self._store = {}
        self._lock = Lock()
        self._default_ttl = default_ttl
        self._max_entries = max_entries
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if time.time() > entry.expires_at:
                del self._store[key]
                self._misses += 1
                return None
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        with self._lock:
            # Evict expired entries if at capacity
            if len(self._store) >= self._max_entries:
                self._evict_expired()

            # If still at capacity, remove oldest entries
            if len(self._store) >= self._max_entries:
                to_remove = list(self._store.keys())[:len(self._store) // 4]
                for k in to_remove:
                    del self._store[k]

            self._store[key] = CacheEntry(value, ttl or self._default_ttl)

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)

    def invalidate_pattern(self, prefix: str):
        """Remove all entries whose key starts with the given prefix."""
        with self._lock:
            keys_to_remove = [k for k in self._store if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._store[k]

    def clear(self):
        with self._lock:
            self._store.clear()

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "entries": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total * 100, 1) if total > 0 else 0,
            }

    def _evict_expired(self):
        now = time.time()
        expired = [k for k, v in self._store.items() if now > v.expires_at]
        for k in expired:
            del self._store[k]


# Global cache instance
cache = InMemoryCache(default_ttl=120, max_entries=2000)


def make_cache_key(prefix: str, **kwargs) -> str:
    """Build a deterministic cache key from prefix and kwargs."""
    parts = json.dumps(kwargs, sort_keys=True)
    h = hashlib.md5(parts.encode()).hexdigest()[:12]
    return f"{prefix}:{h}"


def cached(prefix: str, ttl: int = 120):
    """
    Decorator for caching function results.
    The cache key is built from the prefix and all function arguments.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build key from all args
            key_parts = {
                "args": str(args),
                **{k: str(v) for k, v in kwargs.items()},
            }
            key = make_cache_key(prefix, **key_parts)

            # Check cache
            result = cache.get(key)
            if result is not None:
                return result

            # Execute and cache
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result

        return wrapper
    return decorator
