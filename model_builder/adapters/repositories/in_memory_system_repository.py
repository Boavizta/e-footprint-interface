"""In-memory implementation of ISystemRepository.

This implementation stores system data in memory, primarily for testing purposes.
It allows unit tests__old to run without Django session infrastructure.
"""
from copy import deepcopy
from typing import Dict, Any, Optional

from e_footprint_interface.json_payload_utils import compute_json_size
from model_builder.domain.exceptions import PayloadSizeLimitExceeded
from model_builder.domain.interfaces import ISystemRepository


class InMemorySystemRepository(ISystemRepository):
    """In-memory implementation of system repository.

    This class stores system data in a simple Python dictionary, allowing
    tests__old to run without Django sessions or any external infrastructure.

    Usage:
        # For testing
        repository = InMemorySystemRepository()
        repository.save_system_data({"System": {...}})

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

    def get_system_data(self) -> Optional[Dict[str, Any]]:
        """Retrieve the current system data from memory.

        Returns:
            The system data dictionary, or None if no data exists.
        """
        return self._data

    def save_system_data(
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
