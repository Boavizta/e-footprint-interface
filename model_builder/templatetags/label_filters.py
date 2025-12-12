"""Template filters for label resolution.

These filters handle the presentation concern of resolving raw field/class names
to user-friendly labels, keeping this logic out of domain entities.
"""
from django import template

from model_builder.adapters.label_resolver import LabelResolver

register = template.Library()


@register.filter
def field_label(field_name: str) -> str:
    """Resolve a field name to its display label.

    Usage: {{ field_name|field_label }}

    Args:
        field_name: The raw attribute name (e.g., 'cpu_cores', 'ram')

    Returns:
        User-friendly label, or formatted field_name if not found
    """
    if field_name is None:
        return ""
    label = LabelResolver.get_field_label(field_name)
    if label != field_name:
        return label
    return field_name.replace("_", " ")


@register.filter
def class_label(class_name: str) -> str:
    """Resolve a class name to its display label.

    Usage: {{ class_name|class_label }}

    Args:
        class_name: The simple class name (e.g., 'Server', 'Job')

    Returns:
        User-friendly label
    """
    if class_name is None:
        return ""
    return LabelResolver.get_class_label(class_name)
