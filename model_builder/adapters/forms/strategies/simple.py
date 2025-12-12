"""Simple form strategy for basic single-class creation forms."""
from typing import TYPE_CHECKING, Type

from model_builder.adapters.forms.class_structure import (
    generate_dynamic_form,
    generate_object_creation_structure,
)
from model_builder.adapters.forms.strategies.base import FormStrategy
from model_builder.adapters.forms.strategies.field_utils import (
    apply_field_defaults,
    apply_field_transforms,
    apply_field_transforms_to_fields,
    has_meaningful_dynamic_data,
)
from model_builder.adapters.ui_config.class_ui_config_provider import ClassUIConfigProvider
from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb
    from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class SimpleFormStrategy(FormStrategy):
    """Strategy for simple object creation/edition forms.

    Used for objects with straightforward form requirements:
    - Single or multiple class options
    - Optional field defaults and transforms
    - Optional prerequisites validation

    Examples: UsageJourney, UsageJourneyStep, UsagePattern
    """

    def build_creation_context(
        self,
        web_class: Type["ModelingObjectWeb"],
        object_type: str,
        config: dict,
        efootprint_id_of_parent_to_link_to: str = None
    ) -> dict:
        """Build context for simple object creation.

        Args:
            web_class: The web wrapper class
            object_type: The efootprint class name string
            config: Configuration dict (may be None for default behavior)
            efootprint_id_of_parent_to_link_to: Not used in simple strategy

        Returns:
            Form context dictionary
        """
        # Call get_creation_prerequisites if web_class provides it (for validation)
        if web_class and hasattr(web_class, 'get_creation_prerequisites'):
            web_class.get_creation_prerequisites(self.model_web)

        # Determine available classes
        if config and config.get('available_classes'):
            available_classes = config['available_classes']
        else:
            efootprint_class = MODELING_OBJECT_CLASSES_DICT[object_type]
            available_classes = [efootprint_class]

        # Check if we should use a different object_type for form generation
        form_object_type = object_type
        if config and 'form_object_type' in config:
            form_object_type = config['form_object_type']

        # Generate base context
        form_sections, dynamic_form_data = generate_object_creation_structure(
            form_object_type,
            available_efootprint_classes=available_classes,
            model_web=self.model_web,
        )

        # Apply field defaults if configured
        if config and 'field_defaults' in config:
            apply_field_defaults(form_sections, config['field_defaults'])

        # Apply field transforms if configured
        if config and 'field_transforms' in config:
            apply_field_transforms(form_sections, config['field_transforms'])

        context = {
            "object_type": object_type,
            "form_sections": form_sections,
            "obj_formatting_data": ClassUIConfigProvider.get_config(object_type),
            "header_name": f"Add new {ClassUIConfigProvider.get_label(object_type).lower()}"
        }

        # Only include dynamic_form_data if it has meaningful content
        if has_meaningful_dynamic_data(dynamic_form_data):
            context["dynamic_form_data"] = dynamic_form_data

        return context

    def build_edition_context(
        self,
        obj_to_edit: "ModelingObjectWeb",
        config: dict = None
    ) -> dict:
        """Build context for simple object edition.

        Args:
            obj_to_edit: The web wrapper of the object to edit
            config: Optional form_edition_config for field transforms

        Returns:
            Form context dictionary
        """
        form_fields, form_fields_advanced, dynamic_lists = generate_dynamic_form(
            obj_to_edit.class_as_simple_str,
            obj_to_edit.modeling_obj.__dict__,
            self.model_web
        )

        # Apply field transforms if configured
        if config and 'field_transforms' in config:
            apply_field_transforms_to_fields(form_fields, config['field_transforms'])
            apply_field_transforms_to_fields(form_fields_advanced, config['field_transforms'])

        return {
            "object_to_edit": obj_to_edit,
            "form_fields": form_fields,
            "form_fields_advanced": form_fields_advanced,
            "dynamic_form_data": {"dynamic_lists": dynamic_lists},
            "header_name": f"Edit {obj_to_edit.name}"
        }
