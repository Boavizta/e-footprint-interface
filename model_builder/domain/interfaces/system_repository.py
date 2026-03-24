"""Interface for system data persistence.

This interface defines the contract for storing and retrieving system data.
Implementations can use Django sessions, databases, files, or in-memory storage.

This module has NO Django dependencies, keeping the domain layer framework-agnostic.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple

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

    def get_system_data_with_source(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Retrieve the current system data with a source label.

        Returns:
            (system_data, source) where source can be "redis", "postgres", or another backend label.
        """
        return self.get_system_data(), "unknown"

    def get_interface_config(self) -> dict:
        """Retrieve interface_config from stored system data."""
        data = self.get_system_data()
        return data.get("interface_config", {}) if data else {}

    @property
    def interface_config(self) -> dict:
        """Return in-memory interface config when available."""
        return self.get_interface_config()

    @interface_config.setter
    def interface_config(self, value: dict) -> None:
        self._interface_config = value

    @staticmethod
    def upgrade_system_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Upgrade system data to the latest schema version.

        Args:
            data: The existing system data dictionary.

        Returns:
            The upgraded system data dictionary.
        """
        # Apply interface-specific version upgrades before json_to_system
        if "efootprint_version" not in data:
            data["efootprint_version"] = "9.1.4"
        json_efootprint_version = data.get("efootprint_version")
        if json_efootprint_version:
            json_major_version = int(json_efootprint_version.split(".")[0])
            from model_builder.version_upgrade_handlers import INTERFACE_VERSION_UPGRADE_HANDLERS
            # Apply all interface upgrades for versions > json_major_version
            for version in sorted(INTERFACE_VERSION_UPGRADE_HANDLERS.keys()):
                if version > json_major_version:
                    logger.info(f"Applying interface upgrade handler for version {version}")
                    data = INTERFACE_VERSION_UPGRADE_HANDLERS[version](data)

        if "interface_config" in data:
            from e_footprint_interface import __version__ as interface_version
            from model_builder.version_upgrade_handlers import upgrade_interface_config

            current_major = int(interface_version.split(".")[0])
            json_interface_version = data.get("efootprint_interface_version", "0.14.5")
            json_major = int(json_interface_version.split(".")[0])
            if json_major < current_major:
                data["interface_config"] = upgrade_interface_config(data["interface_config"], json_major)
                data["efootprint_interface_version"] = interface_version

        return data

    @abstractmethod
    def save_data(
        self,
        data: Dict[str, Any],
        data_without_calculated_attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """Persist the system data.

        Args:
            data: The system data dictionary to save.
            data_without_calculated_attributes: Optional version without calculated attributes,
                used for slower persistence layers (e.g., Postgres fallback cache).
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
