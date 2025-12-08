"""In-memory implementation of ISystemRepository.

This implementation stores system data in memory, primarily for testing purposes.
It allows unit tests__old to run without Django session infrastructure.
"""
from copy import deepcopy
from typing import Dict, Any, Optional

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
    """

    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        """Initialize with optional initial data.

        Args:
            initial_data: Optional initial system data dictionary.
                         If provided, a deep copy is made to avoid mutation.
        """
        self._data: Optional[Dict[str, Any]] = deepcopy(initial_data) if initial_data else None

    def get_system_data(self) -> Optional[Dict[str, Any]]:
        """Retrieve the current system data from memory.

        Returns:
            The system data dictionary, or None if no data exists.
        """
        return self._data

    def save_system_data(self, data: Dict[str, Any]) -> None:
        """Store the system data in memory.

        Args:
            data: The system data dictionary to save.
        """
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
