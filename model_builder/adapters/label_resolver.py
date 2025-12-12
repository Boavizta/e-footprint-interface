"""Label resolution for domain objects.

This module provides the concrete implementation of ILabelResolver,
centralizing all UI label lookups. Domain entities use the interface,
and this implementation provides the actual label resolution from JSON config.
"""
from typing import Optional

from model_builder.domain.interfaces import ILabelResolver
from model_builder.form_references import FORM_TYPE_OBJECT, FORM_FIELD_REFERENCES


class LabelResolver(ILabelResolver):
    """Resolves UI labels for domain objects.

    This class provides a clean boundary between domain entities and
    presentation concerns. Instead of domain entities knowing about
    UI labels, they expose raw identifiers and this resolver handles
    the translation to display text.
    """

    @staticmethod
    def get_class_label(class_name: str) -> str:
        """Get display label for a class name.

        Args:
            class_name: The simple class name (e.g., 'Server', 'Job')

        Returns:
            User-friendly label, or class_name if not found
        """
        return FORM_TYPE_OBJECT.get(class_name, {}).get("label", class_name)

    @staticmethod
    def get_field_label(field_name: str) -> str:
        """Get display label for a field name.

        Args:
            field_name: The attribute name (e.g., 'ram', 'cpu_cores')

        Returns:
            User-friendly label, or field_name if not found
        """
        return FORM_FIELD_REFERENCES.get(field_name, {}).get("label", field_name)

    @staticmethod
    def get_field_tooltip(field_name: str) -> Optional[str]:
        """Get tooltip text for a field.

        Args:
            field_name: The attribute name

        Returns:
            Tooltip text, or None if not defined
        """
        return FORM_FIELD_REFERENCES.get(field_name, {}).get("tooltip")

    @staticmethod
    def get_type_object_available_label(class_name: str) -> Optional[str]:
        """Get type object available label for class selection dropdowns.

        Args:
            class_name: The simple class name

        Returns:
            Label for type selection, or None if not defined
        """
        return FORM_TYPE_OBJECT.get(class_name, {}).get("type_object_available")

    @staticmethod
    def get_more_descriptive_label(class_name: str) -> str:
        """Get more descriptive label for select inputs.

        Some classes have a more descriptive label for use in dropdowns
        where additional context is helpful.

        Args:
            class_name: The simple class name

        Returns:
            Descriptive label, falling back to regular label or class_name
        """
        form_config = FORM_TYPE_OBJECT.get(class_name, {})
        return form_config.get("more_descriptive_label_for_select_inputs",
                              form_config.get("label", class_name))

    @staticmethod
    def get_class_config(class_name: str) -> dict:
        """Get full configuration for a class.

        Args:
            class_name: The simple class name

        Returns:
            Configuration dict, or empty dict if not found
        """
        return FORM_TYPE_OBJECT.get(class_name, {})

    @staticmethod
    def get_field_config(field_name: str) -> dict:
        """Get full configuration for a field.

        Args:
            field_name: The attribute name

        Returns:
            Configuration dict, or empty dict if not found
        """
        return FORM_FIELD_REFERENCES.get(field_name, {})
