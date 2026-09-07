"""Shared cache backend helper for Redis/Postgres-backed repositories."""
import os
from datetime import datetime, timezone
from enum import Enum
from time import perf_counter
from typing import Optional

from django.conf import settings
from django.core.cache import caches
from django.db import connections, router, transaction
from django.utils.timezone import now as tz_now
from efootprint.logger import logger


class CacheTouchOutcome(Enum):
    UPDATED = "updated"
    MISSING = "missing"
    ERROR = "error"


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

    def get_from(self, cache_key: str, cache_alias: str):
        """Read one cache backend without falling through to the other representation."""
        cache = self._get_cache(cache_alias)
        if cache is None:
            return None
        return self._time_cache_call(
            "get", cache_alias, lambda: cache.get(cache_key)
        )

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
            set_result = self._time_cache_call(
                "set", self.POSTGRES_CACHE_ALIAS,
                lambda: postgres_cache.set(
                    cache_key,
                    value,
                    timeout=postgres_timeout_seconds or self.POSTGRES_CACHE_TIMEOUT_SECONDS,
                ),
            )
            # DatabaseCache.set returns False when it silently drops a write under DB-lock contention
            # ("allowed to fail silently to be threadsafe"). Surface it so lost writes aren't invisible.
            if set_result is False:
                logger.warning(f"{self.POSTGRES_CACHE_ALIAS} cache set for key {cache_key} was dropped (write lost)")

    def touch_postgres(self, cache_key: str, timeout_seconds: int) -> CacheTouchOutcome:
        """Update a live Postgres cache expiry without reading, rewriting, or reviving its value."""
        postgres_cache = self._get_cache(self.POSTGRES_CACHE_ALIAS)

        def touch_live_row():
            key = postgres_cache.make_and_validate_key(cache_key)
            database = router.db_for_write(postgres_cache.cache_model_class)
            connection = connections[database]
            table = connection.ops.quote_name(settings.CACHES[self.POSTGRES_CACHE_ALIAS]["LOCATION"])
            expires = connection.ops.quote_name("expires")
            cache_key_column = connection.ops.quote_name("cache_key")
            now = tz_now().replace(microsecond=0)
            backend_timeout = postgres_cache.get_backend_timeout(timeout_seconds)
            tz = timezone.utc if settings.USE_TZ else None
            new_expiry = datetime.fromtimestamp(backend_timeout, tz=tz).replace(microsecond=0)
            with transaction.atomic(using=database), connection.cursor() as cursor:
                cursor.execute(
                    f"UPDATE {table} SET {expires} = %s WHERE {cache_key_column} = %s AND {expires} > %s",
                    [
                        connection.ops.adapt_datetimefield_value(new_expiry),
                        key,
                        connection.ops.adapt_datetimefield_value(now),
                    ],
                )
                return CacheTouchOutcome.UPDATED if cursor.rowcount == 1 else CacheTouchOutcome.MISSING

        return self._time_cache_call(
            "touch",
            self.POSTGRES_CACHE_ALIAS,
            touch_live_row,
            default=CacheTouchOutcome.ERROR,
        )

    def delete_expired_postgres(self, now) -> int:
        """Delete expired rows from the configured Postgres cache table."""
        postgres_cache = self._get_cache(self.POSTGRES_CACHE_ALIAS)
        database = router.db_for_write(postgres_cache.cache_model_class)
        connection = connections[database]
        table = connection.ops.quote_name(settings.CACHES[self.POSTGRES_CACHE_ALIAS]["LOCATION"])
        expires = connection.ops.quote_name("expires")
        adapted_now = connection.ops.adapt_datetimefield_value(now)
        with connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {table} WHERE {expires} < %s", [adapted_now])
            return cursor.rowcount

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
