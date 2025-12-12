"""Label resolution for domain objects.

This module provides the concrete implementation of ILabelResolver,
used by domain entities via dependency injection for label resolution.
"""
from model_builder.domain.interfaces import ILabelResolver
from model_builder.adapters.ui_config.class_ui_config_provider import ClassUIConfigProvider
from model_builder.adapters.ui_config.field_ui_config_provider import FieldUIConfigProvider


class LabelResolver(ILabelResolver):
    """Resolves UI labels for domain objects.

    This class provides a clean boundary between domain entities and
    presentation concerns. It delegates to the specialized UI config providers.
    """

    @staticmethod
    def get_class_label(class_name: str) -> str:
        return ClassUIConfigProvider.get_label(class_name)

    @staticmethod
    def get_field_label(field_name: str) -> str:
        return FieldUIConfigProvider.get_label(field_name)
