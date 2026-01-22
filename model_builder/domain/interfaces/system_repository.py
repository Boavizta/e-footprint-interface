"""Interface for system data persistence.

This interface defines the contract for storing and retrieving system data.
Implementations can use Django sessions, databases, files, or in-memory storage.

This module has NO Django dependencies, keeping the domain layer framework-agnostic.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from efootprint.logger import logger


class ISystemRepository(ABC):
    """Interface for system data persistence.

    This abstraction allows the business logic (ModelWeb, use cases) to be
    decoupled from the specific storage mechanism (Django sessions, database, etc.).

    Implementations:
        - SessionSystemRepository: Uses Django sessions (for production)
        - InMemorySystemRepository: Uses in-memory dict (for testing)
    """

    @abstractmethod
    def get_system_data(self) -> Optional[Dict[str, Any]]:
        """Retrieve the current system data.

        Returns:
            The system data dictionary, or None if no data exists.
        """
        pass

    @staticmethod
    def upgrade_system_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Upgrade system data to the latest schema version.

        Args:
            data: The existing system data dictionary.

        Returns:
            The upgraded system data dictionary.
        """
        # Apply interface-specific version upgrades before json_to_system
        json_efootprint_version = data.get("efootprint_version")
        if json_efootprint_version:
            json_major_version = int(json_efootprint_version.split(".")[0])
            from model_builder.version_upgrade_handlers import INTERFACE_VERSION_UPGRADE_HANDLERS
            # Apply all interface upgrades for versions > json_major_version
            for version in sorted(INTERFACE_VERSION_UPGRADE_HANDLERS.keys()):
                if version > json_major_version:
                    logger.info(f"Applying interface upgrade handler for version {version}")
                    data = INTERFACE_VERSION_UPGRADE_HANDLERS[version](data)

        return data

    @abstractmethod
    def save_system_data(self, data: Dict[str, Any]) -> None:
        """Persist the system data.

        Args:
            data: The system data dictionary to save.
        """
        pass

    @abstractmethod
    def has_system_data(self) -> bool:
        """Check if system data exists.

        Returns:
            True if system data exists, False otherwise.
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all system data."""
        pass
