"""In-memory implementation of ISystemRepository and IWorkspaceRepository.

These implementations store system data in memory, primarily for testing purposes.
They allow the integration harness to run without Django session infrastructure
(the in-memory and session repositories stay interchangeable).
"""
from copy import deepcopy
from typing import Dict, Any, List, Optional, Tuple

from e_footprint_interface import __version__ as interface_version
from e_footprint_interface.json_payload_utils import compute_json_size
from model_builder.domain.exceptions import PayloadSizeLimitExceeded
from model_builder.domain.interfaces import ISystemRepository
from model_builder.adapters.repositories.workspace_base import WorkspaceRepositoryBase


class InMemorySystemRepository(ISystemRepository):
    """In-memory implementation of system repository.

    This class stores system data in a simple Python dictionary, allowing
    tests to run without Django sessions or any external infrastructure.

    Usage:
        # For testing
        repository = InMemorySystemRepository()
        repository.save_data({"System": {...}})

        # Or initialize with data
        repository = InMemorySystemRepository(initial_data=test_data)

        # With size limit enforcement (for testing limit behavior)
        repository = InMemorySystemRepository(max_payload_size_mb=30.0)
    """

    def __init__(self, initial_data: Optional[Dict[str, Any]] = None, max_payload_size_mb: Optional[float] = None):
        """Initialize with optional initial data and size limit.

        Args:
            initial_data: Optional initial system data dictionary.
                         If provided, a deep copy is made to avoid mutation.
            max_payload_size_mb: Optional maximum payload size in MB. If set,
                                save_system_data will raise PayloadSizeLimitExceeded
                                when data exceeds this limit.
        """
        self._data: Optional[Dict[str, Any]] = deepcopy(initial_data) if initial_data else None
        self._max_payload_size_mb = max_payload_size_mb
        self._interface_config: Optional[Dict[str, Any]] = (
            deepcopy(initial_data["interface_config"])
            if initial_data and "interface_config" in initial_data
            else None
        )

    def get_system_data(self) -> Optional[Dict[str, Any]]:
        """Retrieve the current system data from memory.

        Returns:
            The system data dictionary, or None if no data exists.
        """
        return self._data

    def get_system_data_with_source(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Retrieve the current system data with a source label."""
        return self._data, "memory" if self._data is not None else None

    @property
    def interface_config(self) -> dict:
        if self._interface_config is None and self._data and "interface_config" in self._data:
            self._interface_config = deepcopy(self._data["interface_config"])
        return {} if self._interface_config is None else self._interface_config

    @interface_config.setter
    def interface_config(self, value: dict) -> None:
        self._interface_config = value

    def save_data(
        self,
        data: Dict[str, Any],
        data_without_calculated_attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store the system data in memory.

        Args:
            data: The system data dictionary to save.
            data_without_calculated_attributes: Optional version without calculated attributes.
                Ignored for the in-memory repository.

        Raises:
            PayloadSizeLimitExceeded: If max_payload_size_mb is set and data exceeds the limit.
        """
        if self._interface_config is not None:
            for payload in (data, data_without_calculated_attributes):
                if payload is not None:
                    payload["interface_config"] = deepcopy(self._interface_config)
                    payload["efootprint_interface_version"] = interface_version

        if self._max_payload_size_mb is not None:
            size_result = compute_json_size(data)
            if size_result.size_mb > self._max_payload_size_mb:
                raise PayloadSizeLimitExceeded(size_result.size_mb, self._max_payload_size_mb)

        self._data = data

    def has_system_data(self) -> bool:
        """Check if system data exists.

        Returns:
            True if system data exists, False otherwise.
        """
        return self._data is not None

    def clear(self) -> None:
        """Clear system data from memory."""
        self._data = None
        self._interface_config = None


class InMemoryWorkspaceRepository(WorkspaceRepositoryBase):
    """In-memory workspace mirroring the session workspace for the integration harness.

    Holds one ``InMemorySystemRepository`` per slot plus an active pointer, and enforces the shared
    payload budget as the *summed* with-calc size over all slots (not per slot), matching the session
    implementation. The distinct-system-id invariant comes from ``WorkspaceRepositoryBase``.
    """

    def __init__(self, initial_data: Optional[Dict[str, Any]] = None, max_payload_size_mb: Optional[float] = None):
        self._max_payload_size_mb = max_payload_size_mb
        self._slots: Dict[int, InMemorySystemRepository] = {0: InMemorySystemRepository(initial_data=initial_data)}
        self._active = 0

    def list_slots(self) -> List[int]:
        return sorted(self._slots)

    def active_slot(self) -> int:
        return self._active

    def set_active_slot(self, slot: int) -> None:
        if slot not in self._slots:
            raise ValueError(f"Cannot activate slot {slot}: not an occupied slot ({self.list_slots()}).")
        self._active = slot

    def repository_for(self, slot: int) -> ISystemRepository:
        return self._slots.setdefault(slot, InMemorySystemRepository())

    def add_slot(self, system_data: Dict[str, Any]) -> int:
        self._check_summed_budget(system_data)
        return super().add_slot(system_data)

    def _register_slot(self, slot: int) -> None:
        # repository_for already materialised the slot when add_slot saved into it.
        self._slots.setdefault(slot, InMemorySystemRepository())

    def _deregister_slot(self, slot: int) -> None:
        self._slots.pop(slot, None)
        if self._active == slot:
            self._active = self.list_slots()[0] if self._slots else 0

    def _check_summed_budget(self, incoming_data: Dict[str, Any]) -> None:
        """Reject when the summed with-calc size over existing slots plus the incoming model exceeds
        the budget — the in-memory mirror of the session shared-budget guard."""
        if self._max_payload_size_mb is None:
            return
        total_bytes = compute_json_size(incoming_data).size_bytes
        for repo in self._slots.values():
            data = repo.get_system_data()
            if data is not None:
                total_bytes += compute_json_size(data).size_bytes
        total_mb = total_bytes / (1024 * 1024)
        if total_mb > self._max_payload_size_mb:
            raise PayloadSizeLimitExceeded(total_mb, self._max_payload_size_mb)
