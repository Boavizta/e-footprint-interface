"""Parent selection form strategy for objects requiring parent selection."""
import re
from typing import TYPE_CHECKING, Type

from model_builder.adapters.forms.form_field_generator import generate_object_creation_structure
from model_builder.adapters.forms.strategies.base import FormStrategy
from model_builder.adapters.ui_config.class_ui_config_provider import ClassUIConfigProvider

if TYPE_CHECKING:
    from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class ParentSelectionFormStrategy(FormStrategy):
    """Strategy for object creation with parent selection.

    Used by Job, RecurrentEdgeDeviceNeed where user must select a parent first,
    and that selection drives which object types are available.

    The web_class must provide:
    - form_creation_config with:
        - parent_attribute: Name of parent field (e.g., 'server', 'edge_device')
        - intermediate_attribute: Optional intermediate selection (e.g., 'service')
        - type_classes_by_parent_class: Optional mapping parent_class -> child_classes
        - Optional parent_attribute_label and intermediate_attribute_label to override default labels
    - get_creation_prerequisites(model_web) -> dict with:
        - parents: List of parent web objects
        - available_classes: List of all possible classes
        - intermediate_by_parent: Optional {parent_id: {items: [...], extra_options: [...]}}
        - type_classes_by_intermediate: Optional {intermediate_id: [classes]}
    """

    def build_creation_context(
        self,
        web_class: Type["ModelingObjectWeb"],
        object_type: str,
        config: dict,
        efootprint_id_of_parent_to_link_to: str = None
    ) -> dict:
        """Build context for object creation with parent selection.

        Args:
            web_class: The web wrapper class
            object_type: The object type string (e.g., 'Job')
            config: The form_creation_config from web_class
            efootprint_id_of_parent_to_link_to: Not used in this strategy

        Returns:
            Form context dictionary with parent selection fields and dynamic selects
        """
        prereqs = web_class.get_creation_prerequisites(self.model_web)

        parent_attr = config['parent_attribute']
        parent_attr_label = config.get('parent_attribute_label', parent_attr.replace('_', ' '))
        intermediate_attr = config.get('intermediate_attribute')
        parents = prereqs['parents']
        available_classes = prereqs['available_classes']

        # Build helper fields
        helper_fields = [self._build_parent_select_field(parent_attr, parent_attr_label, parents)]

        if intermediate_attr:
            intermediate_attr_label = config.get(
                'intermediate_attribute_label', intermediate_attr.replace('_', ' ').title())
            helper_fields.append(self._build_intermediate_select_field(intermediate_attr, intermediate_attr_label))

        # Build dynamic selects
        dynamic_selects = []

        if intermediate_attr:
            # With intermediate: parent -> intermediate -> type
            dynamic_selects.extend(self._build_intermediate_dynamic_selects(
                prereqs, parent_attr, intermediate_attr))
        elif 'type_classes_by_parent_class' in config:
            # No intermediate: parent class determines type directly
            dynamic_selects.append(self._build_type_by_parent_class_select(
                config['type_classes_by_parent_class'], parents, parent_attr))

        # Generate form sections
        form_sections, dynamic_form_data = generate_object_creation_structure(
            object_type,
            available_efootprint_classes=available_classes,
            model_web=self.model_web,
        )

        # Prepend helper fields as first section
        helper_section = {
            "category": f"{object_type.lower()}_creation_helper",
            "header": f"{ClassUIConfigProvider.get_label(object_type)} creation helper",
            "fields": helper_fields
        }
        form_sections = [helper_section] + form_sections

        if dynamic_selects:
            dynamic_form_data["dynamic_selects"] = dynamic_selects

        return {
            "form_sections": form_sections,
            "dynamic_form_data": dynamic_form_data,
            "object_type": object_type,
            "obj_formatting_data": ClassUIConfigProvider.get_config(object_type),
            "header_name": f"Add new {ClassUIConfigProvider.get_label(object_type).lower()}"
        }

    @staticmethod
    def _indefinite_article(phrase: str) -> str:
        match = re.search(r"[A-Za-z]", phrase or "")
        if not match:
            return "a"
        return "an" if match.group(0).lower() in "aeiou" else "a"

    def _build_parent_select_field(self, parent_attr: str, parent_attr_label: str, parents: list) -> dict:
        """Build a select field for parent selection."""
        return {
            "input_type": "select_object",
            "web_id": parent_attr,
            "name": parent_attr_label,
            "options": [{"label": p.name, "value": p.efootprint_id} for p in parents],
            "label": f"Choose {self._indefinite_article(parent_attr_label)} {parent_attr_label}",
        }

    def _build_intermediate_select_field(self, intermediate_attr: str, intermediate_attr_label: str) -> dict:
        """Build a select field for intermediate selection (options filled dynamically)."""
        return {
            "input_type": "select_object",
            "web_id": intermediate_attr,
            "name": intermediate_attr_label,
            "options": None,  # Filled by dynamic select
            "label": f"{intermediate_attr_label} used",
        }

    def _build_intermediate_dynamic_selects(
        self, prereqs: dict, parent_attr: str, intermediate_attr: str
    ) -> list:
        """Build dynamic selects for intermediate pattern (parent -> intermediate -> type)."""
        intermediate_by_parent = prereqs['intermediate_by_parent']
        type_classes_by_intermediate = prereqs.get('type_classes_by_intermediate', {})

        # First select: parent -> intermediate options
        intermediate_options_by_parent = {}
        # Second select: intermediate -> type options
        type_options_by_intermediate = {}

        for parent_id, data in intermediate_by_parent.items():
            items = data.get('items', [])
            extra_options = data.get('extra_options', [])

            # Build options from regular items
            options = [{"label": item.name, "value": item.efootprint_id} for item in items]

            # Add extra options (e.g., "direct call to server")
            for extra in extra_options:
                options.append({"label": extra['label'], "value": extra['id']})
                # Also add type mapping for this extra option
                type_options_by_intermediate[extra['id']] = [
                    {"label": ClassUIConfigProvider.get_label(cls.__name__), "value": cls.__name__}
                    for cls in extra['type_classes']
                ]

            intermediate_options_by_parent[parent_id] = options

        # Build type options for regular intermediate items
        for intermediate_id, classes in type_classes_by_intermediate.items():
            type_options_by_intermediate[intermediate_id] = [
                {"label": ClassUIConfigProvider.get_label(cls.__name__), "value": cls.__name__}
                for cls in classes
            ]

        return [
            {"input_id": intermediate_attr, "filter_by": parent_attr, "list_value": intermediate_options_by_parent},
            {"input_id": "type_object_available", "filter_by": intermediate_attr,
             "list_value": type_options_by_intermediate},
        ]

    def _build_type_by_parent_class_select(
        self, type_classes_by_parent_class: dict, parents: list, parent_attr: str
    ) -> dict:
        """Build dynamic select where type depends on parent's class."""
        type_options_by_parent = {}
        for parent in parents:
            parent_class = parent.class_as_simple_str
            classes = type_classes_by_parent_class.get(parent_class, [])
            type_options_by_parent[parent.efootprint_id] = [
                {"label": ClassUIConfigProvider.get_label(cls.__name__), "value": cls.__name__}
                for cls in classes
            ]
        return {"input_id": "type_object_available", "filter_by": parent_attr, "list_value": type_options_by_parent}
