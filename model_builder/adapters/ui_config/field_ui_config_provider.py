"""Field UI configuration provider.

Provides UI configuration for domain object fields (labels, tooltips, advanced flags, etc.).
"""
from typing import Optional

from model_builder.adapters.ui_config import FIELD_UI_CONFIG


class FieldUIConfigProvider:
    """Provides UI configuration for domain object fields."""

    @staticmethod
    def get_label(field_name: str) -> str:
        """Get display label for a field name."""
        return FIELD_UI_CONFIG.get(field_name, {}).get("label", field_name)

    @staticmethod
    def is_advanced_parameter(field_name: str) -> bool:
        """Check if a field is an advanced parameter."""
        return FIELD_UI_CONFIG.get(field_name, {}).get("is_advanced_parameter", False)

    @staticmethod
    def get_step(field_name: str) -> Optional[int]:
        """Get step value for numeric inputs."""
        return FIELD_UI_CONFIG.get(field_name, {}).get("step")

    @staticmethod
    def get_modeling_obj_containers(field_name: str) -> list:
        """Get list of classes that contain this field."""
        return FIELD_UI_CONFIG.get(field_name, {}).get("modeling_obj_containers", [])

    @staticmethod
    def get_config(field_name: str, class_name: str = None) -> dict:
        """Get full configuration for a field, with class-qualified overrides.

        Entries keyed "ClassName.field_name" override the plain field entry, so attributes shared
        across classes (e.g. `jobs` on UsageJourneyStep and RecurrentServerNeed) can word their
        labels per parent class.
        """
        config = FIELD_UI_CONFIG.get(field_name, {})
        if class_name:
            config = {**config, **FIELD_UI_CONFIG.get(f"{class_name}.{field_name}", {})}
        return config
