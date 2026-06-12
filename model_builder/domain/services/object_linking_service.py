"""Service for linking child objects to parent objects.

This service handles the domain logic for finding the correct child attribute
(list or weighted ExplainableObjectDict) on a parent object and building the
edit data to link a child object.
"""
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional, Tuple, TYPE_CHECKING, get_origin, get_args

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.utils.tools import get_init_signature_params

from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb
    from model_builder.domain.efootprint_to_web_mapping import ModelingObjectWeb


@dataclass
class LinkResult:
    """Result of linking a child to a parent."""
    attr_name: str
    edit_data: dict
    parent_web_obj: "ModelingObjectWeb"


@lru_cache(maxsize=1)
def dict_relationship_registry() -> Tuple[Tuple[type, str, type], ...]:
    """(parent class, attr name, child class) for every `ExplainableObjectDict[X]` init annotation
    across all modeling classes — the single source of truth for dict-relationship resolution."""
    entries = []
    for parent_class in MODELING_OBJECT_CLASSES_DICT.values():
        for attr_name, param in get_init_signature_params(parent_class).items():
            annotation_origin = get_origin(param.annotation)
            if isinstance(annotation_origin, type) and issubclass(annotation_origin, ExplainableObjectDict):
                type_arg = get_args(param.annotation)[0]
                child_class = MODELING_OBJECT_CLASSES_DICT[type_arg] if isinstance(type_arg, str) else type_arg
                entries.append((parent_class, attr_name, child_class))
    return tuple(entries)


def resolve_dict_attr(parent_obj: ModelingObject, key_obj: ModelingObject) -> str:
    """Find the dict attribute on `parent_obj` that can hold `key_obj`, from the cached registry."""
    matches = list(dict.fromkeys(
        attr_name for parent_class, attr_name, child_class in dict_relationship_registry()
        if isinstance(parent_obj, parent_class) and isinstance(key_obj, child_class)))
    if not matches:
        raise ValueError(
            f"Object {key_obj.id} cannot be linked into any dict attribute of "
            f"{type(parent_obj).__name__} {parent_obj.id}.")
    if len(matches) > 1:
        raise ValueError(
            f"Object {key_obj.id} cannot be unambiguously linked into a dict attribute of "
            f"{type(parent_obj).__name__} {parent_obj.id} (matching attributes: {matches}).")
    return matches[0]


def resolve_dict_attr_for_classes(parent_class: type, child_class: type) -> Optional[str]:
    """Dict attribute of `parent_class` that holds `child_class` entries, or None for list/other relations."""
    matches = list(dict.fromkeys(
        attr_name for registry_parent_class, attr_name, registry_child_class in dict_relationship_registry()
        if issubclass(parent_class, registry_parent_class) and issubclass(child_class, registry_child_class)))
    if len(matches) > 1:
        raise ValueError(
            f"{child_class.__name__} cannot be unambiguously linked into a dict attribute of "
            f"{parent_class.__name__} (matching attributes: {matches}).")
    return matches[0] if matches else None


def dict_attr_names_for_class(parent_class: type) -> List[str]:
    """Names of all `ExplainableObjectDict[X]` attributes declared by `parent_class`'s init."""
    return list(dict.fromkeys(
        attr_name for registry_parent_class, attr_name, _ in dict_relationship_registry()
        if issubclass(parent_class, registry_parent_class)))


def dict_membership_specs(child_class: type) -> List[Tuple[type, str]]:
    """(parent class, dict attr name) pairs whose child annotation matches `child_class` —
    the reverse view used by child-panel membership sections."""
    return [(parent_class, attr_name) for parent_class, attr_name, registry_child_class
            in dict_relationship_registry() if issubclass(child_class, registry_child_class)]


def serialize_weighted_dict_entry(value) -> dict:
    """Serialize one weighted-dict value into the parsed-form-data shape, preserving its label and source."""
    entry = {"value": value.value.magnitude, "unit": "dimensionless", "label": value.label}
    if value.source is not None:
        entry["source"] = value.source.to_json()
    return entry


class ObjectLinkingService:
    """Service for linking child modeling objects to parent objects.

    This service encapsulates the domain logic for:
    - Finding which child attribute on a parent accepts a given child type
      (a `List[ChildType]` or a weighted `ExplainableObjectDict[ChildType]`)
    - Building the edit data needed to add the child to that attribute
    """

    def find_child_attribute_for_child(
        self, parent_obj: ModelingObject, child_obj: ModelingObject) -> Optional[str]:
        """Find the list or dict attribute on the parent that can contain the child type.

        Args:
            parent_obj: The parent modeling object
            child_obj: The child modeling object to link

        Returns:
            The attribute name if found, None otherwise
        """
        init_sig_params = get_init_signature_params(type(parent_obj))
        for attr_name, param in init_sig_params.items():
            annotation = param.annotation
            annotation_origin = get_origin(annotation)
            if annotation_origin in (list, List):
                if isinstance(child_obj, get_args(annotation)[0]):
                    return attr_name
            elif isinstance(annotation_origin, type) and issubclass(annotation_origin, ExplainableObjectDict):
                type_arg = get_args(annotation)[0]
                child_class = MODELING_OBJECT_CLASSES_DICT[type_arg] if isinstance(type_arg, str) else type_arg
                if isinstance(child_obj, child_class):
                    return attr_name
        return None

    def build_link_edit_data(self, parent_obj: ModelingObject, child_id: str, attr_name: str,
                             count: float = 1) -> dict:
        """Build the edit data to add a child to a parent's child attribute.

        For list attributes the edit data is the list of linked ids; for weighted dict attributes
        it is a `{child_id: {value, unit, label}}` mapping with the new entry at `count` (1 by
        default), labeled with the parent class's static weight label (`weight_labels`). Existing
        entries are re-serialized as-is so their weights, labels and sources are preserved.

        Args:
            parent_obj: The parent modeling object
            child_id: The ID of the child object to add
            attr_name: The name of the child attribute on the parent
            count: The weight of the new entry (dict attributes only)

        Returns:
            Dict with the attribute name mapped to its post-link parsed value
        """
        existing_elements = getattr(parent_obj, attr_name)
        if isinstance(existing_elements, ExplainableObjectDict):
            entries = {key.id: serialize_weighted_dict_entry(value) for key, value in existing_elements.items()}
            entries[child_id] = {
                "value": count, "unit": "dimensionless", "label": type(parent_obj).weight_labels[attr_name]}
            return {attr_name: entries}
        existing_ids = [elt.id for elt in existing_elements]
        existing_ids.append(child_id)
        return {attr_name: existing_ids}

    def link_child_to_parent(self, model_web: "ModelWeb", child_web_obj: "ModelingObjectWeb", parent_id: str,
                             count: float = 1) -> LinkResult:
        """Link a child object to its parent.

        This method finds the correct child attribute and builds the edit data,
        but does NOT perform the actual edit (that's the caller's responsibility).

        Args:
            model_web: The ModelWeb instance
            child_web_obj: The child web object to link
            parent_id: The efootprint ID of the parent object
            count: The weight of the new entry when the relationship is a weighted dict

        Returns:
            LinkResult containing the attribute name, edit data, and parent web object

        Raises:
            AssertionError: If no suitable child attribute is found on the parent
        """
        parent_web_obj = model_web.get_web_object_from_efootprint_id(parent_id)
        parent_modeling_obj = parent_web_obj.modeling_obj
        child_modeling_obj = child_web_obj.modeling_obj

        attr_name = self.find_child_attribute_for_child(parent_modeling_obj, child_modeling_obj)
        assert attr_name is not None, "A child attr name should always be found"

        edit_data = self.build_link_edit_data(parent_modeling_obj, child_web_obj.efootprint_id, attr_name, count)

        return LinkResult(attr_name=attr_name, edit_data=edit_data, parent_web_obj=parent_web_obj)
