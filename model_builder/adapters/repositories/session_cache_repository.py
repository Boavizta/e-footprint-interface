"""Session-scoped cache repository backed by Redis and Postgres caches."""
from typing import Optional

from django.contrib.sessions.backends.base import SessionBase

from model_builder.adapters.repositories.cache_backend import CacheBackend


class SessionCacheRepository:
    """Session-keyed cache repository with Redis + Postgres backends."""

    DEFAULT_NAMESPACE = "session_cache"

    def __init__(self, session: SessionBase, namespace: Optional[str] = None):
        self._session = session
        self._namespace = namespace or self.DEFAULT_NAMESPACE
        self._cache_backend = CacheBackend()

    def _cache_key(self, key: str, create_if_missing: bool = True) -> Optional[str]:
        session_key = self._session.session_key
        if not session_key and create_if_missing:
            self._session.save()
            session_key = self._session.session_key
        if not session_key:
            return None
        return f"{self._namespace}:{session_key}:{key}"

    def get(self, key: str) -> Optional[str]:
        cache_key = self._cache_key(key, create_if_missing=False)
        if not cache_key:
            return None
        return self._cache_backend.get(cache_key)

    def set(
        self,
        key: str,
        value: str,
        redis_timeout_seconds: Optional[int] = None,
        postgres_timeout_seconds: Optional[int] = None,
        write_redis: bool = True,
        write_postgres: bool = True,
    ) -> None:
        cache_key = self._cache_key(key, create_if_missing=True)
        if not cache_key:
            return
        self._cache_backend.set(
            cache_key,
            value,
            redis_timeout_seconds=redis_timeout_seconds,
            postgres_timeout_seconds=postgres_timeout_seconds,
            write_redis=write_redis,
            write_postgres=write_postgres
        )

    def delete(self, key: str) -> None:
        cache_key = self._cache_key(key, create_if_missing=False)
        if not cache_key:
            return
        self._cache_backend.delete(cache_key)

    def pop(self, key: str) -> Optional[str]:
        value = self.get(key)
        if value is not None:
            self.delete(key)
        return value
