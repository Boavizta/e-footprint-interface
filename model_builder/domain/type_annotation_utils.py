from types import UnionType
from typing import Union, get_args, get_origin


def resolve_optional_annotation(annotation):
    """Unwrap `X | None` / `Optional[X]` annotations to `X`."""
    origin = get_origin(annotation)
    if origin not in (Union, UnionType):
        return annotation

    non_none_args = [arg for arg in get_args(annotation) if arg is not type(None)]
    if len(non_none_args) == 1:
        return non_none_args[0]

    return annotation
