"""Service for linking child objects to parent objects.

This service handles the domain logic for finding the correct list attribute
on a parent object and building the edit data to link a child object.
"""
from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING, get_origin, get_args

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.utils.tools import get_init_signature_params

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb
    from model_builder.efootprint_to_web_mapping import ModelingObjectWeb


@dataclass
class LinkResult:
    """Result of linking a child to a parent."""
    attr_name: str
    edit_data: dict
    parent_web_obj: "ModelingObjectWeb"


class ObjectLinkingService:
    """Service for linking child modeling objects to parent objects.

    This service encapsulates the domain logic for:
    - Finding which list attribute on a parent accepts a given child type
    - Building the edit data needed to add the child to the parent's list
    """

    def find_list_attribute_for_child(self, parent_obj: ModelingObject, child_obj: ModelingObject) -> Optional[str]:
        """Find the list attribute on the parent that can contain the child type.

        Args:
            parent_obj: The parent modeling object
            child_obj: The child modeling object to link

        Returns:
            The attribute name if found, None otherwise
        """
        init_sig_params = get_init_signature_params(type(parent_obj))
        for attr_name, param in init_sig_params.items():
            annotation = param.annotation
            if get_origin(annotation) and get_origin(annotation) in (list, List):
                list_item_type = get_args(annotation)[0]
                if isinstance(child_obj, list_item_type):
                    return attr_name
        return None

    def build_link_edit_data(self, parent_obj: ModelingObject, child_id: str, attr_name: str) -> dict:
        """Build the edit data to add a child to a parent's list attribute.

        Args:
            parent_obj: The parent modeling object
            child_id: The ID of the child object to add
            attr_name: The name of the list attribute on the parent

        Returns:
            Dict with the attribute name and semicolon-separated IDs
        """
        existing_elements = getattr(parent_obj, attr_name)
        existing_ids = [elt.id for elt in existing_elements]
        existing_ids.append(child_id)
        return {attr_name: ";".join(existing_ids)}

    def link_child_to_parent(self, model_web: "ModelWeb", child_web_obj: "ModelingObjectWeb", parent_id: str) -> LinkResult:
        """Link a child object to its parent.

        This method finds the correct list attribute and builds the edit data,
        but does NOT perform the actual edit (that's the caller's responsibility).

        Args:
            model_web: The ModelWeb instance
            child_web_obj: The child web object to link
            parent_id: The efootprint ID of the parent object

        Returns:
            LinkResult containing the attribute name, edit data, and parent web object

        Raises:
            AssertionError: If no suitable list attribute is found on the parent
        """
        parent_web_obj = model_web.get_web_object_from_efootprint_id(parent_id)
        parent_modeling_obj = parent_web_obj.modeling_obj
        child_modeling_obj = child_web_obj.modeling_obj

        attr_name = self.find_list_attribute_for_child(parent_modeling_obj, child_modeling_obj)
        assert attr_name is not None, "A list attr name should always be found"

        edit_data = self.build_link_edit_data(parent_modeling_obj, child_web_obj.efootprint_id, attr_name)

        return LinkResult(attr_name=attr_name, edit_data=edit_data, parent_web_obj=parent_web_obj)
