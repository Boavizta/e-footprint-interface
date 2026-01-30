"""Session-keyed implementation of ISystemRepository.

This implementation stores system data in Redis (fast cache) with a Postgres
fallback cache, keyed by the Django session identifier.
"""
import os
from typing import Dict, Any, Optional, Tuple

from django.contrib.sessions.backends.base import SessionBase
from efootprint.logger import logger

from e_footprint_interface.json_payload_utils import compute_json_size
from model_builder.domain.exceptions import PayloadSizeLimitExceeded
from model_builder.domain.interfaces import ISystemRepository
from model_builder.adapters.repositories.cache_backend import CacheBackend


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
        self._cache_backend = CacheBackend()

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
        if cache_key:
            cached_data, source = self._cache_backend.get_with_source(cache_key)
            if cached_data is not None:
                if source == "postgres":
                    logger.info("No data in Redis cache; falling back to Postgres cache.")
                return cached_data, source

        # Todo: suppress legacy data part end of Feb 2026
        legacy_data = self._session.get(self.SYSTEM_DATA_KEY)
        if legacy_data is not None:
            if cache_key:
                self._cache_backend.set(
                    cache_key,
                    legacy_data,
                    redis_timeout_seconds=self.REDIS_CACHE_TIMEOUT_SECONDS,
                    postgres_timeout_seconds=self.POSTGRES_CACHE_TIMEOUT_SECONDS,
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

        postgres_payload = data_without_calculated_attributes or data

        if cache_key:
            self._session.modified = True
            self._cache_backend.set(
                cache_key,
                data,
                redis_timeout_seconds=self.REDIS_CACHE_TIMEOUT_SECONDS,
                write_postgres=False,
            )
            self._cache_backend.set(
                cache_key,
                postgres_payload,
                postgres_timeout_seconds=self.POSTGRES_CACHE_TIMEOUT_SECONDS,
                write_redis=False,
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
        if cache_key:
            cached_data = self._cache_backend.get(cache_key)
            if cached_data is not None:
                return True
        return self.SYSTEM_DATA_KEY in self._session

    def clear(self) -> None:
        """Clear system data from Redis, Postgres, and the session."""
        cache_key = self._cache_key(create_if_missing=False)
        if cache_key:
            self._cache_backend.delete(cache_key)

        self._session.pop(self.SYSTEM_DATA_KEY, None)
        self._session.modified = True

    @property
    def session(self) -> SessionBase:
        """Access the underlying session (for backwards compatibility during migration).

        This property allows gradual migration of code that still needs
        direct session access. It should be used sparingly and eventually removed.
        """
        return self._session
