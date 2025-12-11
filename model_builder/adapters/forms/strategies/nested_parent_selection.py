"""Nested parent selection form strategy for child objects needing internal selection."""
from typing import TYPE_CHECKING, Type

from model_builder.adapters.forms.class_structure import generate_object_creation_structure
from model_builder.adapters.forms.strategies.base import FormStrategy
from model_builder.form_references import FORM_TYPE_OBJECT

if TYPE_CHECKING:
    from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class NestedParentSelectionFormStrategy(FormStrategy):
    """Strategy for child objects with parent known but needing internal selection.

    Used by RecurrentEdgeComponentNeed where parent (RecurrentEdgeDeviceNeed) is known,
    but user must still select an edge component from the parent's device.

    The web_class must provide:
    - get_form_creation_data(model_web, parent_id) -> dict with:
        - 'available_classes': List of efootprint classes
        - 'helper_fields': List of field dicts for component selection
        - 'parent_context_key': Key for storing parent in context
        - 'parent': The parent object to store
        - 'extra_dynamic_data': Optional dict to merge into dynamic_form_data
    """

    def build_creation_context(
        self,
        web_class: Type["ModelingObjectWeb"],
        object_type: str,
        config: dict,
        efootprint_id_of_parent_to_link_to: str = None
    ) -> dict:
        """Build context for child object with internal selection.

        Args:
            web_class: The web wrapper class
            object_type: The object type string (e.g., 'RecurrentEdgeComponentNeed')
            config: The form_creation_config from web_class
            efootprint_id_of_parent_to_link_to: Required parent object ID

        Returns:
            Form context dictionary with parent and component selection
        """
        # Get form data from domain class method
        form_data = web_class.get_form_creation_data(self.model_web, efootprint_id_of_parent_to_link_to)

        available_classes = form_data['available_classes']
        helper_fields = form_data['helper_fields']
        parent_context_key = form_data.get('parent_context_key')
        parent = form_data.get('parent')
        extra_dynamic_data = form_data.get('extra_dynamic_data', {})

        # Generate form sections
        form_sections, dynamic_form_data = generate_object_creation_structure(
            object_type,
            available_efootprint_classes=available_classes,
            model_web=self.model_web,
        )

        # Prepend helper fields as first section
        helper_section = {
            "category": f"{object_type.lower()}_creation_helper",
            "header": f"{FORM_TYPE_OBJECT.get(object_type, {'label': object_type})['label']} creation helper",
            "fields": helper_fields
        }
        form_sections = [helper_section] + form_sections

        # Merge extra dynamic data
        dynamic_form_data.update(extra_dynamic_data)

        context_data = {
            "form_sections": form_sections,
            "dynamic_form_data": dynamic_form_data,
            "object_type": object_type,
            "obj_formatting_data": FORM_TYPE_OBJECT.get(object_type, {"label": object_type}),
            "header_name": f"Add new {FORM_TYPE_OBJECT.get(object_type, {'label': object_type})['label'].lower()}"
        }

        # Add parent to context with specified key
        if parent_context_key and parent:
            context_data[parent_context_key] = parent

        return context_data
