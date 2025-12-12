"""With-storage form strategy for objects that have an associated storage."""
from typing import TYPE_CHECKING, Type

from model_builder.adapters.forms.form_field_generator import (
    generate_dynamic_form,
    generate_object_creation_structure,
)
from model_builder.adapters.forms.strategies.base import FormStrategy
from model_builder.adapters.label_resolver import LabelResolver

if TYPE_CHECKING:
    from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class WithStorageFormStrategy(FormStrategy):
    """Strategy for objects that create/edit a storage alongside.

    Used by Server, EdgeDevice, EdgeComputer which have an associated storage
    object that is created/edited together with the main object.

    Config requirements for creation:
        - available_classes: List of available main object classes
        - storage_type: Storage type string (e.g., 'Storage')
        - storage_classes: List of available storage classes
    """

    def build_creation_context(
        self,
        web_class: Type["ModelingObjectWeb"],
        object_type: str,
        config: dict,
        efootprint_id_of_parent_to_link_to: str = None
    ) -> dict:
        """Build context for object with storage creation.

        Args:
            web_class: The web wrapper class
            object_type: Main object type string (e.g., 'ServerBase')
            config: Configuration dict with available_classes, storage_type, storage_classes
            efootprint_id_of_parent_to_link_to: Not used in this strategy

        Returns:
            Form context dictionary with both object and storage form sections
        """
        available_classes = config['available_classes']
        storage_type = config['storage_type']
        storage_classes = config['storage_classes']

        # Generate form sections for main object
        form_sections, dynamic_form_data = generate_object_creation_structure(
            object_type,
            available_efootprint_classes=available_classes,
            model_web=self.model_web,
        )

        # Generate form sections for storage
        storage_form_sections, storage_dynamic_form_data = generate_object_creation_structure(
            storage_type,
            available_efootprint_classes=storage_classes,
            model_web=self.model_web,
        )

        return {
            "object_type": object_type,
            "form_sections": form_sections,
            "dynamic_form_data": dynamic_form_data,
            "storage_form_sections": storage_form_sections,
            "storage_dynamic_form_data": storage_dynamic_form_data,
            "header_name": f"Add new {LabelResolver.get_class_label(object_type).lower()}"
        }

    def build_edition_context(
        self,
        obj_to_edit: "ModelingObjectWeb",
        config: dict = None
    ) -> dict:
        """Build context for object with storage edition.

        Args:
            obj_to_edit: The web wrapper of the object to edit (must have .storage attribute)
            config: Optional form_edition_config (not used currently)

        Returns:
            Form context dictionary with both object and storage form fields
        """
        storage_to_edit = obj_to_edit.storage

        # Generate form fields for main object
        form_fields, form_fields_advanced, dynamic_lists = generate_dynamic_form(
            obj_to_edit.class_as_simple_str,
            obj_to_edit.modeling_obj.__dict__,
            self.model_web
        )

        context_data = {
            "object_to_edit": obj_to_edit,
            "form_fields": form_fields,
            "form_fields_advanced": form_fields_advanced,
            "dynamic_form_data": {"dynamic_lists": dynamic_lists},
            "header_name": f"Edit {obj_to_edit.name}"
        }

        # Generate form fields for storage
        storage_form_fields, storage_form_fields_advanced, storage_dynamic_lists = generate_dynamic_form(
            storage_to_edit.class_as_simple_str,
            storage_to_edit.modeling_obj.__dict__,
            storage_to_edit.model_web
        )

        context_data.update({
            "storage_to_edit": storage_to_edit,
            "storage_form_fields": storage_form_fields,
            "storage_form_fields_advanced": storage_form_fields_advanced,
            "storage_dynamic_form_data": {"dynamic_lists": storage_dynamic_lists},
        })

        return context_data
