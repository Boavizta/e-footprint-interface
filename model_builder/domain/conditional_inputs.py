"""Resolve conditional constructor inputs without presentation-specific identifiers."""

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject


def resolve_input_path(root: ModelingObject, path: str) -> tuple[ModelingObject, str]:
    """Return the actual owner and final attribute of a dotted input path."""
    *relationships, attribute = path.split(".")
    owner = root
    for name in relationships:
        owner = getattr(owner, name)
    return owner, attribute
