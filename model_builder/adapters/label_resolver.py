"""Label resolution for UI presentation.

This module provides a unified interface for label resolution,
delegating to specialized UI config providers.
"""
from model_builder.adapters.ui_config.class_ui_config_provider import ClassUIConfigProvider
from model_builder.adapters.ui_config.field_ui_config_provider import FieldUIConfigProvider


class LabelResolver:
    """Resolves UI labels for presentation.

    This class provides a unified interface for label resolution,
    delegating to the specialized UI config providers.
    """

    @staticmethod
    def get_class_label(class_name: str) -> str:
        return ClassUIConfigProvider.get_label(class_name)

    @staticmethod
    def get_field_label(field_name: str) -> str:
        return FieldUIConfigProvider.get_label(field_name)
