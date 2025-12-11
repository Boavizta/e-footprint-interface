"""Child-of-parent form strategy for child objects with known parent."""
from typing import TYPE_CHECKING, Type

from model_builder.adapters.forms.class_structure import generate_object_creation_structure
from model_builder.adapters.forms.strategies.base import FormStrategy
from model_builder.form_references import FORM_TYPE_OBJECT

if TYPE_CHECKING:
    from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class ChildOfParentFormStrategy(FormStrategy):
    """Strategy for child object creation with parent already known.

    Used by Service (child of Server) and EdgeComponent (child of EdgeDevice).
    The parent is already selected when the form opens.

    Config requirements:
        - available_classes: List of available classes, OR
        - get_available_classes_from_parent: Method name to call on parent to get classes
        - parent_context_key: Key to store parent in context (e.g., 'server', 'edge_device')
    """

    def build_creation_context(
        self,
        web_class: Type["ModelingObjectWeb"],
        object_type: str,
        config: dict,
        efootprint_id_of_parent_to_link_to: str = None
    ) -> dict:
        """Build context for child object creation.

        Args:
            web_class: The web wrapper class
            object_type: Child object type string (e.g., 'Service', 'EdgeComponent')
            config: Configuration dict with available_classes or get_available_classes_from_parent
            efootprint_id_of_parent_to_link_to: Required parent object ID

        Returns:
            Form context dictionary with parent reference
        """
        parent_context_key = config.get('parent_context_key')

        # Get parent object
        parent = self.model_web.get_web_object_from_efootprint_id(efootprint_id_of_parent_to_link_to)

        # Get available classes - either static or dynamic from parent
        if 'get_available_classes_from_parent' in config:
            method_name = config['get_available_classes_from_parent']
            available_classes = getattr(parent, method_name)()
        else:
            available_classes = config['available_classes']

        # Generate form sections
        form_sections, dynamic_form_data = generate_object_creation_structure(
            object_type,
            available_efootprint_classes=available_classes,
            model_web=self.model_web,
        )

        context_data = {
            "form_sections": form_sections,
            "dynamic_form_data": dynamic_form_data,
            "object_type": object_type,
            "obj_formatting_data": FORM_TYPE_OBJECT[object_type],
            "header_name": f"Add new {FORM_TYPE_OBJECT[object_type]['label'].lower()}",
        }

        # Add parent to context with specified key
        if parent_context_key:
            context_data[parent_context_key] = parent

        return context_data
