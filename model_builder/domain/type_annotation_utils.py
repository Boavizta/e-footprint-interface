from types import UnionType
from typing import Union, get_args, get_origin

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject


def resolve_optional_annotation(annotation):
    """Resolve the editable type of an input that also permits None or an empty value."""
    origin = get_origin(annotation)
    if origin not in (Union, UnionType):
        return annotation

    value_types = [arg for arg in get_args(annotation) if arg not in (type(None), EmptyExplainableObject)]
    if len(value_types) == 1:
        return value_types[0]

    return annotation
