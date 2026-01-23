"""Session-keyed implementation of ISystemRepository.

This implementation stores system data in Redis (fast cache) with a Postgres
fallback cache, keyed by the Django session identifier.
"""
import os
from time import perf_counter
from typing import Dict, Any, Optional, Tuple

from django.contrib.sessions.backends.base import SessionBase
from django.core.cache import caches
from django.core.cache.backends.base import InvalidCacheBackendError
from efootprint.logger import logger

from e_footprint_interface.json_payload_utils import compute_json_size
from model_builder.domain.exceptions import PayloadSizeLimitExceeded
from model_builder.domain.interfaces import ISystemRepository


class SessionSystemRepository(ISystemRepository):
    """Session-keyed system repository with Redis + Postgres caches.

    Usage:
        repository = SessionSystemRepository(request.session)
        data = repository.get_system_data()
        repository.save_system_data(modified_data)
    """

    SYSTEM_DATA_KEY = "system_data"
    REDIS_CACHE_ALIAS = os.environ.get("SYSTEM_DATA_REDIS_CACHE_ALIAS", "redis")
    POSTGRES_CACHE_ALIAS = os.environ.get("SYSTEM_DATA_POSTGRES_CACHE_ALIAS", "postgres")
    REDIS_CACHE_TIMEOUT_SECONDS = int(os.environ.get("SYSTEM_DATA_REDIS_TTL_SECONDS", "600"))
    POSTGRES_CACHE_TIMEOUT_SECONDS = int(os.environ.get("SYSTEM_DATA_POSTGRES_TTL_SECONDS", "43200"))
    MAX_PAYLOAD_SIZE_MB = float(os.environ.get("MAX_PAYLOAD_SIZE_MB", 30.0))

    def __init__(self, session: SessionBase):
        """Initialize with a Django session.

        Args:
            session: The Django session object (typically request.session)
        """
        self._session = session

    def _get_cache(self, alias: str):
        try:
            return caches[alias]
        except InvalidCacheBackendError:
            logger.warning(f"Cache backend '{alias}' is not configured; falling back to session storage.")
            return None

    @staticmethod
    def _time_cache_call(action: str, cache_name: str, fn):
        start = perf_counter()
        result = fn()
        elapsed_ms = (perf_counter() - start) * 1000
        logger.info(f"{cache_name} cache {action} took {elapsed_ms:.1f} ms")
        return result

    def _cache_key(self, create_if_missing: bool = True) -> Optional[str]:
        session_key = self._session.session_key
        if not session_key and create_if_missing:
            self._session.save()
            session_key = self._session.session_key
        if not session_key:
            return None
        return f"{self.SYSTEM_DATA_KEY}:{session_key}"

    def get_system_data(self) -> Optional[Dict[str, Any]]:
        """Retrieve the current system data from Redis, falling back to Postgres.

        Returns:
            The system data dictionary, or None if no data exists.
        """
        data, _source = self.get_system_data_with_source()
        return data

    def get_system_data_with_source(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Retrieve the current system data with a source label.

        Returns:
            (system_data, source) where source can be "redis", "postgres", "session", or None.
        """
        cache_key = self._cache_key(create_if_missing=True)
        redis_cache = self._get_cache(self.REDIS_CACHE_ALIAS)
        postgres_cache = self._get_cache(self.POSTGRES_CACHE_ALIAS)

        if cache_key and redis_cache is not None:
            cached_data = self._time_cache_call(
                "get", self.REDIS_CACHE_ALIAS, lambda: redis_cache.get(cache_key)
            )
            if cached_data is not None:
                return cached_data, "redis"

        if cache_key and postgres_cache is not None:
            logger.info("No data in Redis cache; falling back to Postgres cache.")
            cached_data = self._time_cache_call(
                "get", self.POSTGRES_CACHE_ALIAS, lambda: postgres_cache.get(cache_key)
            )
            if cached_data is not None:
                return cached_data, "postgres"

        # Todo: suppress legacy data part end of Feb 2026
        legacy_data = self._session.get(self.SYSTEM_DATA_KEY)
        if legacy_data is not None:
            if cache_key and redis_cache is not None:
                self._time_cache_call(
                    "set", self.REDIS_CACHE_ALIAS,
                    lambda: redis_cache.set(
                        cache_key, legacy_data, timeout=self.REDIS_CACHE_TIMEOUT_SECONDS
                    ),
                )
            if cache_key and postgres_cache is not None:
                self._time_cache_call(
                    "set", self.POSTGRES_CACHE_ALIAS,
                    lambda: postgres_cache.set(
                        cache_key, legacy_data, timeout=self.POSTGRES_CACHE_TIMEOUT_SECONDS
                    ),
                )
            self._session.pop(self.SYSTEM_DATA_KEY, None)
            self._session.modified = True
            return legacy_data, "session"
        return None, None

    def save_system_data(
        self,
        data: Dict[str, Any],
        data_without_calculated_attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """Persist the system data to Redis and Postgres.

        Args:
            data: The system data dictionary to save.
            data_without_calculated_attributes: Optional version without calculated attributes.

        Raises:
            PayloadSizeLimitExceeded: If the data exceeds MAX_PAYLOAD_SIZE_MB.
        """
        size_result = compute_json_size(data)
        logger.info(
            f"System data JSON size: {size_result.size_mb:.2f} MB "
            f"(computation took {size_result.computation_time_ms:.1f} ms)"
        )

        if size_result.size_mb > self.MAX_PAYLOAD_SIZE_MB:
            raise PayloadSizeLimitExceeded(size_result.size_mb, self.MAX_PAYLOAD_SIZE_MB)

        cache_key = self._cache_key(create_if_missing=True)
        redis_cache = self._get_cache(self.REDIS_CACHE_ALIAS)
        postgres_cache = self._get_cache(self.POSTGRES_CACHE_ALIAS)

        postgres_payload = data_without_calculated_attributes or data

        if cache_key and redis_cache is not None:
            self._time_cache_call(
                "set", self.REDIS_CACHE_ALIAS,
                lambda: redis_cache.set(
                    cache_key, data, timeout=self.REDIS_CACHE_TIMEOUT_SECONDS
                ),
            )
        if cache_key and postgres_cache is not None:
            self._time_cache_call(
                "set", self.POSTGRES_CACHE_ALIAS,
                lambda: postgres_cache.set(
                    cache_key, postgres_payload, timeout=self.POSTGRES_CACHE_TIMEOUT_SECONDS
                ),
            )

        if self.SYSTEM_DATA_KEY in self._session:
            self._session.pop(self.SYSTEM_DATA_KEY, None)
            self._session.modified = True

    def has_system_data(self) -> bool:
        """Check if system data exists in Redis or Postgres.

        Returns:
            True if system data exists, False otherwise.
        """
        cache_key = self._cache_key(create_if_missing=False)
        redis_cache = self._get_cache(self.REDIS_CACHE_ALIAS)
        postgres_cache = self._get_cache(self.POSTGRES_CACHE_ALIAS)

        if cache_key and redis_cache is not None:
            cached_data = self._time_cache_call(
                "get", self.REDIS_CACHE_ALIAS, lambda: redis_cache.get(cache_key)
            )
            if cached_data is not None:
                return True
        if cache_key and postgres_cache is not None:
            cached_data = self._time_cache_call(
                "get", self.POSTGRES_CACHE_ALIAS, lambda: postgres_cache.get(cache_key)
            )
            if cached_data is not None:
                return True
        return self.SYSTEM_DATA_KEY in self._session

    def clear(self) -> None:
        """Clear system data from Redis, Postgres, and the session."""
        cache_key = self._cache_key(create_if_missing=False)
        redis_cache = self._get_cache(self.REDIS_CACHE_ALIAS)
        postgres_cache = self._get_cache(self.POSTGRES_CACHE_ALIAS)

        if cache_key and redis_cache is not None:
            self._time_cache_call(
                "delete", self.REDIS_CACHE_ALIAS, lambda: redis_cache.delete(cache_key)
            )
        if cache_key and postgres_cache is not None:
            self._time_cache_call(
                "delete", self.POSTGRES_CACHE_ALIAS, lambda: postgres_cache.delete(cache_key)
            )

        self._session.pop(self.SYSTEM_DATA_KEY, None)
        self._session.modified = True

    @property
    def session(self) -> SessionBase:
        """Access the underlying session (for backwards compatibility during migration).

        This property allows gradual migration of code that still needs
        direct session access. It should be used sparingly and eventually removed.
        """
        return self._session
