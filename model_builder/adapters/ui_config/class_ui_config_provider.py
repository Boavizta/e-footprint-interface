"""Class UI configuration provider.

Provides UI configuration for domain classes (labels, type selectors, etc.).
"""
from typing import Optional

from model_builder.adapters.ui_config import CLASS_UI_CONFIG


class ClassUIConfigProvider:
    """Provides UI configuration for domain classes."""

    @staticmethod
    def get_label(class_name: str) -> str:
        """Get display label for a class name."""
        return CLASS_UI_CONFIG.get(class_name, {}).get("label", class_name)

    @staticmethod
    def get_type_object_available_label(class_name: str) -> Optional[str]:
        """Get type object available label for class selection dropdowns."""
        return CLASS_UI_CONFIG.get(class_name, {}).get("type_object_available")

    @staticmethod
    def get_more_descriptive_label(class_name: str) -> str:
        """Get more descriptive label for select inputs."""
        config = CLASS_UI_CONFIG.get(class_name, {})
        return config.get("more_descriptive_label_for_select_inputs", config.get("label", class_name))

    @staticmethod
    def get_config(class_name: str) -> dict:
        """Get full configuration for a class."""
        return CLASS_UI_CONFIG.get(class_name, {})
