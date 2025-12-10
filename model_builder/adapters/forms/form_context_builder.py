"""Form context builder for generating form structures.

This module provides the FormContextBuilder class which generates form contexts
for object creation and edition. This is adapter-layer code that reads declarative
configuration from domain entities and generates presentation-ready form structures.

The key principle is:
- Domain entities declare WHAT (configuration/data)
- This adapter decides HOW (generates actual form structures)
"""
from typing import TYPE_CHECKING, List, Type

from model_builder.adapters.forms.class_structure import (
    generate_dynamic_form,
    generate_object_creation_context as _generate_creation_context,
    generate_object_creation_structure,
)
from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.form_references import FORM_TYPE_OBJECT

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb
    from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class FormContextBuilder:
    """Builds form contexts for domain objects.

    This class reads declarative configuration from domain entities and generates
    the appropriate form structures. Domain entities should not call form generation
    functions directly - they provide configuration, this class does the generation.

    Supported strategies:
    - "simple": Basic single-class creation form (default)
    - "with_storage": Object + storage dual form (for Server, EdgeDevice, EdgeComputer)
    """

    def __init__(self, model_web: "ModelWeb"):
        """Initialize with a ModelWeb instance.

        Args:
            model_web: The ModelWeb instance for accessing system data
        """
        self.model_web = model_web

    def build_creation_context(
        self,
        web_class: Type["ModelingObjectWeb"],
        object_type: str,
        efootprint_id_of_parent_to_link_to: str = None
    ) -> dict:
        """Build form context for object creation.

        Reads the form_creation_config from the web class and generates
        the appropriate form structure.

        Args:
            web_class: The web wrapper class (e.g., ServerWeb, JobWeb)
            object_type: The efootprint class name string
            efootprint_id_of_parent_to_link_to: Optional parent object ID

        Returns:
            Dictionary with form context data ready for template rendering
        """
        # Get form configuration from web class
        config = getattr(web_class, 'form_creation_config', None)

        if config is None:
            # Default: simple pattern with single class
            return self._build_simple_creation_context(object_type)

        strategy = config.get('strategy', 'simple')

        if strategy == 'simple':
            available_classes = config.get('available_classes')
            return self._build_simple_creation_context(object_type, available_classes)
        elif strategy == 'with_storage':
            return self._build_with_storage_creation_context(config)
        else:
            raise ValueError(f"Unknown form strategy: {strategy}")

    def _build_simple_creation_context(
        self,
        object_type: str,
        available_classes: List = None
    ) -> dict:
        """Build context for simple object creation (Pattern 1).

        Args:
            object_type: The efootprint class name string
            available_classes: Optional list of available classes. If None,
                              uses the single class matching object_type.

        Returns:
            Form context dictionary
        """
        if available_classes is None:
            efootprint_class = MODELING_OBJECT_CLASSES_DICT[object_type]
            available_classes = [efootprint_class]

        return _generate_creation_context(object_type, available_classes, self.model_web)

    def _build_with_storage_creation_context(self, config: dict) -> dict:
        """Build context for object with storage creation (Pattern 2).

        Used by Server, EdgeDevice, EdgeComputer which create a storage alongside.

        Args:
            config: Configuration dict with:
                - object_type: Main object type string (e.g., 'ServerBase')
                - available_classes: List of available main object classes
                - storage_type: Storage type string (e.g., 'Storage')
                - storage_classes: List of available storage classes

        Returns:
            Form context dictionary with both object and storage form sections
        """
        object_type = config['object_type']
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
            "header_name": f"Add new {FORM_TYPE_OBJECT[object_type]['label'].lower()}"
        }

    def build_edition_context(self, obj_to_edit: "ModelingObjectWeb") -> dict:
        """Build form context for object edition.

        Args:
            obj_to_edit: The web wrapper of the object to edit

        Returns:
            Dictionary with form context data ready for template rendering
        """
        # Get form configuration from web class
        web_class = type(obj_to_edit)
        config = getattr(web_class, 'form_edition_config', None)

        if config is None:
            # Default: simple edition
            return self._build_simple_edition_context(obj_to_edit)

        strategy = config.get('strategy', 'simple')

        if strategy == 'simple':
            return self._build_simple_edition_context(obj_to_edit)
        elif strategy == 'with_storage':
            return self._build_with_storage_edition_context(obj_to_edit)
        else:
            raise ValueError(f"Unknown form edition strategy: {strategy}")

    def _build_simple_edition_context(self, obj_to_edit: "ModelingObjectWeb") -> dict:
        """Build context for simple object edition.

        Args:
            obj_to_edit: The web wrapper of the object to edit

        Returns:
            Form context dictionary
        """
        form_fields, form_fields_advanced, dynamic_lists = generate_dynamic_form(
            obj_to_edit.class_as_simple_str,
            obj_to_edit.modeling_obj.__dict__,
            self.model_web
        )

        return {
            "object_to_edit": obj_to_edit,
            "form_fields": form_fields,
            "form_fields_advanced": form_fields_advanced,
            "dynamic_form_data": {"dynamic_lists": dynamic_lists},
            "header_name": f"Edit {obj_to_edit.name}"
        }

    def _build_with_storage_edition_context(self, obj_to_edit: "ModelingObjectWeb") -> dict:
        """Build context for object with storage edition (Pattern 2).

        Used by Server, EdgeDevice, EdgeComputer which have an associated storage.

        Args:
            obj_to_edit: The web wrapper of the object to edit (must have .storage attribute)

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
