"""Shared cache backend helper for Redis/Postgres-backed repositories."""
import os
from time import perf_counter
from typing import Optional

from django.core.cache import caches
from efootprint.logger import logger


class CacheBackend:
    """Cache backend wrapper with timing and Redis/Postgres fallback."""

    REDIS_CACHE_ALIAS = os.environ.get(
        "CACHE_REDIS_CACHE_ALIAS",
        os.environ.get("SYSTEM_DATA_REDIS_CACHE_ALIAS", "redis"),
    )
    POSTGRES_CACHE_ALIAS = os.environ.get(
        "CACHE_POSTGRES_CACHE_ALIAS",
        os.environ.get("SYSTEM_DATA_POSTGRES_CACHE_ALIAS", "postgres"),
    )
    REDIS_CACHE_TIMEOUT_SECONDS = int(os.environ.get("CACHE_REDIS_TTL_SECONDS", "600"))
    POSTGRES_CACHE_TIMEOUT_SECONDS = int(os.environ.get("CACHE_POSTGRES_TTL_SECONDS", "43200"))

    @staticmethod
    def _get_cache(alias: str):
        return caches[alias]

    @staticmethod
    def _time_cache_call(action: str, cache_name: str, fn, default=None, swallow_exceptions: bool = True):
        start = perf_counter()
        try:
            result = fn()
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = (perf_counter() - start) * 1000
            logger.warning(
                f"{cache_name} cache {action} failed after {elapsed_ms:.1f} ms: {exc}"
            )
            if swallow_exceptions:
                return default
            raise
        elapsed_ms = (perf_counter() - start) * 1000
        logger.info(f"{cache_name} cache {action} took {elapsed_ms:.1f} ms")
        return result

    def get(self, cache_key: str):
        redis_cache = self._get_cache(self.REDIS_CACHE_ALIAS)
        postgres_cache = self._get_cache(self.POSTGRES_CACHE_ALIAS)

        if redis_cache is not None:
            cached_data = self._time_cache_call(
                "get", self.REDIS_CACHE_ALIAS, lambda: redis_cache.get(cache_key)
            )
            if cached_data is not None:
                return cached_data

        if postgres_cache is not None:
            cached_data = self._time_cache_call(
                "get", self.POSTGRES_CACHE_ALIAS, lambda: postgres_cache.get(cache_key)
            )
            if cached_data is not None:
                return cached_data

        return None

    def get_with_source(self, cache_key: str):
        redis_cache = self._get_cache(self.REDIS_CACHE_ALIAS)
        postgres_cache = self._get_cache(self.POSTGRES_CACHE_ALIAS)

        if redis_cache is not None:
            cached_data = self._time_cache_call(
                "get", self.REDIS_CACHE_ALIAS, lambda: redis_cache.get(cache_key)
            )
            if cached_data is not None:
                return cached_data, "redis"

        if postgres_cache is not None:
            cached_data = self._time_cache_call(
                "get", self.POSTGRES_CACHE_ALIAS, lambda: postgres_cache.get(cache_key)
            )
            if cached_data is not None:
                return cached_data, "postgres"

        return None, None

    def set(
        self,
        cache_key: str,
        value,
        redis_timeout_seconds: Optional[int] = None,
        postgres_timeout_seconds: Optional[int] = None,
        write_redis: bool = True,
        write_postgres: bool = True,
    ) -> None:
        redis_cache = self._get_cache(self.REDIS_CACHE_ALIAS)
        postgres_cache = self._get_cache(self.POSTGRES_CACHE_ALIAS)

        if write_redis and redis_cache is not None:
            self._time_cache_call(
                "set", self.REDIS_CACHE_ALIAS,
                lambda: redis_cache.set(
                    cache_key,
                    value,
                    timeout=redis_timeout_seconds or self.REDIS_CACHE_TIMEOUT_SECONDS,
                ),
            )
        if write_postgres and postgres_cache is not None:
            self._time_cache_call(
                "set", self.POSTGRES_CACHE_ALIAS,
                lambda: postgres_cache.set(
                    cache_key,
                    value,
                    timeout=postgres_timeout_seconds or self.POSTGRES_CACHE_TIMEOUT_SECONDS,
                ),
            )

    def delete(self, cache_key: str) -> None:
        redis_cache = self._get_cache(self.REDIS_CACHE_ALIAS)
        postgres_cache = self._get_cache(self.POSTGRES_CACHE_ALIAS)

        if redis_cache is not None:
            self._time_cache_call(
                "delete", self.REDIS_CACHE_ALIAS, lambda: redis_cache.delete(cache_key)
            )
        if postgres_cache is not None:
            self._time_cache_call(
                "delete", self.POSTGRES_CACHE_ALIAS, lambda: postgres_cache.delete(cache_key)
            )
