"""Interface for label resolution.

This interface defines the contract for resolving UI labels from class/field names.
The domain layer uses this interface, and the adapters layer provides the implementation.

This follows the Dependency Inversion Principle - domain defines the interface,
adapters provide the implementation.
"""
from abc import ABC, abstractmethod


class ILabelResolver(ABC):
    """Interface for resolving UI labels.

    Domain entities need display labels but shouldn't know about JSON config files
    or other presentation concerns. This interface allows the domain to request
    labels while the actual resolution logic lives in the adapters layer.
    """

    @abstractmethod
    def get_class_label(self, class_name: str) -> str:
        """Get display label for a class name.

        Args:
            class_name: The simple class name (e.g., 'Server', 'Job')

        Returns:
            User-friendly label
        """
        pass

    @abstractmethod
    def get_field_label(self, field_name: str) -> str:
        """Get display label for a field name.

        Args:
            field_name: The attribute name (e.g., 'ram', 'cpu_cores')

        Returns:
            User-friendly label
        """
        pass
