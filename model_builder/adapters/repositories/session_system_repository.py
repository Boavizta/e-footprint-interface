"""Session-keyed implementation of ISystemRepository.

This implementation stores system data in Redis (fast cache) with a Postgres
fallback cache, keyed by the Django session identifier and the workspace slot.
"""
import os
from typing import Dict, Any, Optional, Tuple

from django.contrib.sessions.backends.base import SessionBase
from efootprint.logger import logger
from e_footprint_interface import __version__ as interface_version

from e_footprint_interface.json_payload_utils import compute_json_size
from model_builder.domain.exceptions import PayloadSizeLimitExceeded
from model_builder.domain.interfaces import ISystemRepository
from model_builder.adapters.repositories.cache_backend import CacheBackend
from model_builder.adapters.repositories.workspace_index import WorkspaceIndex


class SessionSystemRepository(ISystemRepository):
    """Session-keyed system repository for one workspace slot, with Redis + Postgres caches.

    A repository is bound to a single slot; with no explicit slot it resolves the workspace's
    active slot, so the single-model call sites construct it unchanged. The shared payload budget
    (the summed with-calc weight of every slot) is enforced on save from the slot-size index in the
    session — siblings are read from the index, never re-serialized.

    Usage:
        repository = SessionSystemRepository(request.session)          # active slot
        repository = SessionSystemRepository(request.session, slot=1)  # explicit slot
        data = repository.get_system_data()
        repository.save_data(modified_data)
    """

    SYSTEM_DATA_KEY = "system_data"
    INTERFACE_CONFIG_SESSION_KEY = "interface_config"
    INTERFACE_VERSION_SESSION_KEY = "efootprint_interface_version"
    REDIS_CACHE_ALIAS = os.environ.get("SYSTEM_DATA_REDIS_CACHE_ALIAS", "redis")
    POSTGRES_CACHE_ALIAS = os.environ.get("SYSTEM_DATA_POSTGRES_CACHE_ALIAS", "postgres")
    REDIS_CACHE_TIMEOUT_SECONDS = int(os.environ.get("SYSTEM_DATA_REDIS_TTL_SECONDS", "600"))
    POSTGRES_CACHE_TIMEOUT_SECONDS = int(os.environ.get("SYSTEM_DATA_POSTGRES_TTL_SECONDS", "43200"))
    MAX_PAYLOAD_SIZE_MB = float(os.environ.get("MAX_PAYLOAD_SIZE_MB", 30.0))

    def __init__(self, session: SessionBase, slot: Optional[int] = None):
        """Initialize with a Django session, optionally bound to a specific slot.

        Args:
            session: The Django session object (typically request.session).
            slot: The workspace slot this repository addresses. Defaults to the active slot.
        """
        self._session = session
        self._cache_backend = CacheBackend()
        self._interface_config: Optional[Dict[str, Any]] = None
        self._index = WorkspaceIndex(session)
        self._slot = self._index.active_slot() if slot is None else slot

    @property
    def slot(self) -> int:
        return self._slot

    def _cache_key(self, create_if_missing: bool = True) -> Optional[str]:
        session_key = self._session.session_key
        if not session_key and create_if_missing:
            self._session.save()
            session_key = self._session.session_key
        if not session_key:
            return None
        return f"{self.SYSTEM_DATA_KEY}:{session_key}:{self._slot}"

    def _legacy_cache_key(self) -> Optional[str]:
        """The pre-workspace unsuffixed key. Read once for slot 0 only (one-release fallback).

        Migration note lives in model_builder/version_upgrade_handlers.py; remove next release.
        """
        if self._slot != 0:
            return None
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
            (system_data, source) where source can be "redis", "postgres", or None.
        """
        cache_key = self._cache_key(create_if_missing=True)
        if cache_key:
            cached_data, source = self._cache_backend.get_with_source(cache_key)
            if cached_data is None:
                cached_data, source = self._read_legacy_with_write_through()
            if cached_data is not None:
                if source == "postgres":
                    logger.info("No data in Redis cache; falling back to Postgres cache.")
                if self._interface_config is None and "interface_config" in cached_data:
                    # Only adopt the payload's config; an absent key leaves the session fallback
                    # (interface_config property) reachable.
                    self._interface_config = cached_data["interface_config"]
                return cached_data, source
        return None, None

    def _read_legacy_with_write_through(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """One-release fallback: read an in-flight slot-0 payload from the unsuffixed key and write
        it through to the suffixed key so the legacy key is read at most once per session."""
        legacy_key = self._legacy_cache_key()
        if not legacy_key:
            return None, None
        cached_data, source = self._cache_backend.get_with_source(legacy_key)
        if cached_data is None:
            return None, None
        suffixed_key = self._cache_key(create_if_missing=True)
        if suffixed_key:
            self._cache_backend.set(
                suffixed_key, cached_data,
                redis_timeout_seconds=self.REDIS_CACHE_TIMEOUT_SECONDS,
                postgres_timeout_seconds=self.POSTGRES_CACHE_TIMEOUT_SECONDS,
            )
            self._cache_backend.delete(legacy_key)
            self._index.set_slot_size(self._slot, compute_json_size(cached_data).size_bytes)
            self._session.modified = True
        return cached_data, source

    def load_interface_config_from_session(self) -> dict:
        """Load interface config fallback from Django session."""
        config = self._session.get(self.INTERFACE_CONFIG_SESSION_KEY, {})
        json_interface_version = self._session.get(self.INTERFACE_VERSION_SESSION_KEY, "0.14.5")

        if config:
            from model_builder.version_upgrade_handlers import upgrade_interface_config

            current_major = int(interface_version.split(".")[0])
            json_major = int(json_interface_version.split(".")[0])
            if json_major < current_major:
                config = upgrade_interface_config(config, json_major)
                self._session[self.INTERFACE_CONFIG_SESSION_KEY] = config
                self._session[self.INTERFACE_VERSION_SESSION_KEY] = interface_version
                self._session.modified = True

        return config

    def _save_interface_config_to_session(self) -> None:
        """Persist interface config fallback into Django session."""
        if self._interface_config is None:
            return
        self._session[self.INTERFACE_CONFIG_SESSION_KEY] = self._interface_config
        self._session[self.INTERFACE_VERSION_SESSION_KEY] = interface_version
        self._session.modified = True

    @property
    def interface_config(self) -> dict:
        """Return the repository-scoped interface config."""
        if self._interface_config is None:
            self.get_system_data_with_source()
        if self._interface_config is None:
            self._interface_config = self.load_interface_config_from_session()
        return {} if self._interface_config is None else self._interface_config

    @interface_config.setter
    def interface_config(self, value: dict) -> None:
        self._interface_config = value

    def save_data(
        self,
        data: Dict[str, Any],
        data_without_calculated_attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """Persist the system data to Redis and Postgres.

        Args:
            data: The system data dictionary to save.
            data_without_calculated_attributes: Optional version without calculated attributes.

        Raises:
            PayloadSizeLimitExceeded: If the summed with-calc weight of all slots exceeds
                MAX_PAYLOAD_SIZE_MB (the shared workspace budget).
        """
        if self._interface_config is not None:
            for payload in (data, data_without_calculated_attributes):
                if payload is not None:
                    payload["interface_config"] = self._interface_config
                    payload["efootprint_interface_version"] = interface_version
            self._save_interface_config_to_session()

        size_result = compute_json_size(data)
        logger.info(
            f"System data JSON size (slot {self._slot}): {size_result.size_mb:.2f} MB "
            f"(computation took {size_result.computation_time_ms:.1f} ms)"
        )

        workspace_size_mb = self._index.workspace_size_mb_with(self._slot, size_result.size_bytes)
        if workspace_size_mb > self.MAX_PAYLOAD_SIZE_MB:
            raise PayloadSizeLimitExceeded(workspace_size_mb, self.MAX_PAYLOAD_SIZE_MB)

        cache_key = self._cache_key(create_if_missing=True)

        postgres_payload = data_without_calculated_attributes or data

        if cache_key:
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
            self._index.set_slot_size(self._slot, size_result.size_bytes)
            self._session.modified = True

        if self.SYSTEM_DATA_KEY in self._session:
            self._session.pop(self.SYSTEM_DATA_KEY, None)
            self._session.modified = True

    def has_system_data(self) -> bool:
        """Check if system data exists in Redis or Postgres.

        Returns:
            True if system data exists, False otherwise.
        """
        cache_key = self._cache_key(create_if_missing=False)
        if cache_key and self._cache_backend.get(cache_key) is not None:
            return True
        legacy_key = self._legacy_cache_key()
        if legacy_key and self._cache_backend.get(legacy_key) is not None:
            return True
        return self.SYSTEM_DATA_KEY in self._session

    def clear(self) -> None:
        """Clear this slot's system data from Redis, Postgres, the index, and the session."""
        cache_key = self._cache_key(create_if_missing=False)
        if cache_key:
            self._cache_backend.delete(cache_key)
        legacy_key = self._legacy_cache_key()
        if legacy_key:
            self._cache_backend.delete(legacy_key)

        self._index.forget_slot_size(self._slot)
        self._session.pop(self.SYSTEM_DATA_KEY, None)
        self._session.pop(self.INTERFACE_CONFIG_SESSION_KEY, None)
        self._session.pop(self.INTERFACE_VERSION_SESSION_KEY, None)
        self._session.modified = True
        self._interface_config = None

    @property
    def session(self) -> SessionBase:
        """Access the underlying session (for backwards compatibility during migration).

        This property allows gradual migration of code that still needs
        direct session access. It should be used sparingly and eventually removed.
        """
        return self._session
