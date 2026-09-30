"""Session-keyed implementation of ISystemRepository.

This implementation stores system data in Redis (fast cache) with a Postgres
fallback cache, keyed by the Django session identifier and the workspace slot.
"""
import os
from copy import deepcopy
from typing import Dict, Any, Optional, Tuple

from django.contrib.sessions.backends.base import SessionBase
from efootprint.logger import logger
from e_footprint_interface import __version__ as interface_version

from e_footprint_interface.json_payload_utils import compute_json_size
from model_builder.domain.exceptions import PayloadSizeLimitExceeded
from model_builder.domain.interfaces import ISystemRepository
from model_builder.adapters.repositories.cache_backend import CacheBackend
from model_builder.adapters.repositories.recovery_retention import (
    SYSTEM_DATA_CACHE_NAMESPACE,
    get_recovery_retention_seconds,
)
from model_builder.adapters.repositories.workspace_index import WorkspaceIndex
from model_builder.adapters.repositories.workspace_base import system_id_of


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

    SYSTEM_DATA_KEY = SYSTEM_DATA_CACHE_NAMESPACE
    INTERFACE_CONFIG_SESSION_KEY = "interface_config"
    INTERFACE_VERSION_SESSION_KEY = "efootprint_interface_version"
    REDIS_CACHE_ALIAS = os.environ.get("SYSTEM_DATA_REDIS_CACHE_ALIAS", "redis")
    POSTGRES_CACHE_ALIAS = os.environ.get("SYSTEM_DATA_POSTGRES_CACHE_ALIAS", "postgres")
    REDIS_CACHE_TIMEOUT_SECONDS = int(os.environ.get("SYSTEM_DATA_REDIS_TTL_SECONDS", "3600"))
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
        self._system_id = None
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

    def _recovery_timeout_seconds(self) -> int:
        return get_recovery_retention_seconds(self._session)

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
                self._system_id = system_id_of(cached_data)
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
                postgres_timeout_seconds=self._recovery_timeout_seconds(),
            )
            self._cache_backend.delete(legacy_key)
            self._index.set_slot_size(self._slot, compute_json_size(cached_data).size_bytes)
            self._session.modified = True
        return cached_data, source

    def load_interface_config_from_session(self) -> dict:
        """Recover only settings belonging to this slot's current System."""
        saved = self._session.get(self.INTERFACE_CONFIG_SESSION_KEY, {}).get(str(self._slot), {})
        if self._system_id is None or saved.get("system_id") != self._system_id:
            return {}
        config = deepcopy(saved.get("config", {}))
        from model_builder.version_upgrade_handlers import upgrade_interface_config

        json_major = int(saved.get("version", "0.14.5").split(".")[0])
        if json_major < int(interface_version.split(".")[0]):
            config = upgrade_interface_config(config, json_major)
        return config

    def _save_interface_config_to_session(self) -> None:
        """Publish a copied fallback scoped by slot and System identity."""
        if self._interface_config is None or self._system_id is None:
            return
        saved = dict(self._session.get(self.INTERFACE_CONFIG_SESSION_KEY, {}))
        saved[str(self._slot)] = {"system_id": self._system_id, "config": deepcopy(self._interface_config),
                                  "version": interface_version}
        self._session[self.INTERFACE_CONFIG_SESSION_KEY] = saved
        self._session.modified = True

    @property
    def interface_config(self) -> dict:
        """Return the repository-scoped interface config."""
        if self._interface_config is None:
            self.get_system_data_with_source()
        if self._interface_config is None:
            self._interface_config = self.load_interface_config_from_session()
        from model_builder.version_upgrade_handlers import normalize_interface_config

        self._interface_config = normalize_interface_config(self._interface_config or {})
        return self._interface_config

    @interface_config.setter
    def interface_config(self, value: dict) -> None:
        self._interface_config = value

    def save_interface_config(self) -> None:
        """Persist UI metadata while preserving each backend's existing system representation."""
        if self._interface_config is None:
            return

        cache_key = self._cache_key(create_if_missing=True)
        if not cache_key:
            self._save_interface_config_to_session()
            return

        redis_alias = self._cache_backend.REDIS_CACHE_ALIAS
        postgres_alias = self._cache_backend.POSTGRES_CACHE_ALIAS
        redis_data = self._cache_backend.get_from(cache_key, redis_alias)
        postgres_data = self._cache_backend.get_from(cache_key, postgres_alias)

        def with_interface_config(data):
            if data is None:
                return None
            return {
                **data,
                "interface_config": deepcopy(self._interface_config),
                "efootprint_interface_version": interface_version,
            }

        original_postgres_data = postgres_data
        redis_data = with_interface_config(redis_data)
        postgres_data = with_interface_config(postgres_data)

        budget_data = redis_data if redis_data is not None else postgres_data
        if budget_data is not None:
            size_result = compute_json_size(budget_data)
            slot_size_bytes = size_result.size_bytes
            if redis_data is None:
                # Retain the canonical weight when only compact recovery data remains available.
                previous_size = self._index.slot_sizes().get(self._slot, 0)
                metadata_delta = slot_size_bytes - compute_json_size(original_postgres_data).size_bytes
                slot_size_bytes = max(slot_size_bytes, previous_size + metadata_delta)
            workspace_size_mb = self._index.workspace_size_mb_with(self._slot, slot_size_bytes)
            if workspace_size_mb > self.MAX_PAYLOAD_SIZE_MB:
                raise PayloadSizeLimitExceeded(workspace_size_mb, self.MAX_PAYLOAD_SIZE_MB)

        if redis_data is not None:
            self._cache_backend.set(
                cache_key,
                redis_data,
                redis_timeout_seconds=self.REDIS_CACHE_TIMEOUT_SECONDS,
                write_postgres=False,
            )
        if budget_data is not None:
            self._index.set_slot_size(self._slot, slot_size_bytes)
        if postgres_data is not None:
            self._cache_backend.set(
                cache_key,
                postgres_data,
                postgres_timeout_seconds=self._recovery_timeout_seconds(),
                write_redis=False,
            )

        self._system_id = system_id_of(budget_data)
        self._save_interface_config_to_session()

    def save_data(self, data: Dict[str, Any], recovery_data: Optional[Dict[str, Any]] = None) -> None:
        """Persist canonical data to Redis and compact recovery data to Postgres.

        Args:
            data: Canonical data for the fast Redis path, including stored computed state.
            recovery_data: Optional inputs-only data for the slower Postgres fallback. When omitted,
                ``data`` is used for both backends.

        Raises:
            PayloadSizeLimitExceeded: If the summed weight of all slots exceeds MAX_PAYLOAD_SIZE_MB
                (the shared workspace budget).
        """
        if self._interface_config is not None:
            for payload in (data, recovery_data):
                if payload is not None:
                    payload["interface_config"] = deepcopy(self._interface_config)
                    payload["efootprint_interface_version"] = interface_version

        size_result = compute_json_size(data)
        logger.info(
            f"System data JSON size (slot {self._slot}): {size_result.size_mb:.2f} MB "
            f"(computation took {size_result.computation_time_ms:.1f} ms)"
        )

        workspace_size_mb = self._index.workspace_size_mb_with(self._slot, size_result.size_bytes)
        if workspace_size_mb > self.MAX_PAYLOAD_SIZE_MB:
            raise PayloadSizeLimitExceeded(workspace_size_mb, self.MAX_PAYLOAD_SIZE_MB)

        cache_key = self._cache_key(create_if_missing=True)
        postgres_payload = recovery_data if recovery_data is not None else data

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
                postgres_timeout_seconds=self._recovery_timeout_seconds(),
                write_redis=False,
            )
            self._index.set_slot_size(self._slot, size_result.size_bytes)
            self._session.modified = True

        self._system_id = system_id_of(data)
        if self._interface_config is None and "interface_config" in data:
            self._interface_config = deepcopy(data["interface_config"])
        self._save_interface_config_to_session()

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
        saved = dict(self._session.get(self.INTERFACE_CONFIG_SESSION_KEY, {}))
        saved.pop(str(self._slot), None)
        if saved:
            self._session[self.INTERFACE_CONFIG_SESSION_KEY] = saved
        else:
            self._session.pop(self.INTERFACE_CONFIG_SESSION_KEY, None)
        self._session.pop(self.INTERFACE_VERSION_SESSION_KEY, None)
        self._session.modified = True
        self._interface_config = None
        self._system_id = None

    @property
    def session(self) -> SessionBase:
        """Access the underlying session (for backwards compatibility during migration).

        This property allows gradual migration of code that still needs
        direct session access. It should be used sparingly and eventually removed.
        """
        return self._session
