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
    - "child_of_parent": Child object with parent already known (for Service, EdgeComponent)
    - "parent_selection": Complex parent selection with cascading dynamic selects (for Job, RecurrentEdgeDeviceNeed)
    - "nested_parent_selection": Child with parent already known, but needs internal selection (RecurrentEdgeComponentNeed)
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
            return self._build_simple_creation_context(object_type, web_class=web_class)

        strategy = config.get('strategy', 'simple')

        if strategy == 'simple':
            available_classes = config.get('available_classes')
            return self._build_simple_creation_context(object_type, available_classes, config, web_class)
        elif strategy == 'with_storage':
            return self._build_with_storage_creation_context(object_type, config)
        elif strategy == 'child_of_parent':
            return self._build_child_of_parent_creation_context(object_type, config, efootprint_id_of_parent_to_link_to)
        elif strategy == 'parent_selection':
            return self._build_parent_selection_creation_context(web_class, object_type)
        elif strategy == 'nested_parent_selection':
            return self._build_nested_parent_selection_creation_context(
                web_class, object_type, efootprint_id_of_parent_to_link_to)
        else:
            raise ValueError(f"Unknown form strategy: {strategy}")

    def _build_simple_creation_context(
        self,
        object_type: str,
        available_classes: List = None,
        config: dict = None,
        web_class: Type["ModelingObjectWeb"] = None
    ) -> dict:
        """Build context for simple object creation (Pattern 1).

        Args:
            object_type: The efootprint class name string
            available_classes: Optional list of available classes. If None,
                              uses the single class matching object_type.
            config: Optional full config dict for advanced options
            web_class: Optional web class for calling get_creation_prerequisites

        Returns:
            Form context dictionary
        """
        # Call get_creation_prerequisites if web_class provides it (for validation)
        if web_class and hasattr(web_class, 'get_creation_prerequisites'):
            web_class.get_creation_prerequisites(self.model_web)

        if available_classes is None:
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
            self._apply_field_defaults(form_sections, config['field_defaults'])

        # Apply field transforms if configured
        if config and 'field_transforms' in config:
            self._apply_field_transforms(form_sections, config['field_transforms'])

        return {
            "object_type": object_type,
            "form_sections": form_sections,
            "dynamic_form_data": dynamic_form_data,
            "obj_formatting_data": FORM_TYPE_OBJECT[object_type],
            "header_name": f"Add new {FORM_TYPE_OBJECT[object_type]['label'].lower()}"
        }

    def _build_with_storage_creation_context(self, object_type: str, config: dict) -> dict:
        """Build context for object with storage creation (Pattern 2).

        Used by Server, EdgeDevice, EdgeComputer which create a storage alongside.

        Args:
            object_type: Main object type string (e.g., 'ServerBase')
            config: Configuration dict with:
                - available_classes: List of available main object classes
                - storage_type: Storage type string (e.g., 'Storage')
                - storage_classes: List of available storage classes

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
            "header_name": f"Add new {FORM_TYPE_OBJECT[object_type]['label'].lower()}"
        }

    def _build_child_of_parent_creation_context(
        self,
        object_type: str,
        config: dict,
        efootprint_id_of_parent_to_link_to: str
    ) -> dict:
        """Build context for child object creation with parent already known (Pattern 3).

        Used by Service (child of Server) and EdgeComponent (child of EdgeDevice).

        Args:
            object_type: Child object type string (e.g., 'Service', 'EdgeComponent')
            config: Configuration dict with:
                - available_classes: List of available classes, OR
                - get_available_classes_from_parent: Method name to call on parent to get classes
                - parent_context_key: Key to store parent in context (e.g., 'server', 'edge_device')
                - header_name: Optional custom header name

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
            return self._build_simple_edition_context(obj_to_edit, config)
        elif strategy == 'with_storage':
            return self._build_with_storage_edition_context(obj_to_edit)
        else:
            raise ValueError(f"Unknown form edition strategy: {strategy}")

    def _build_simple_edition_context(self, obj_to_edit: "ModelingObjectWeb", config: dict = None) -> dict:
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
            self._apply_field_transforms_to_fields(form_fields, config['field_transforms'])
            self._apply_field_transforms_to_fields(form_fields_advanced, config['field_transforms'])

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

    def _build_parent_selection_creation_context(
        self,
        web_class: Type["ModelingObjectWeb"],
        object_type: str
    ) -> dict:
        """Build context for object creation with parent selection (Pattern 4).

        Used by Job, RecurrentEdgeDeviceNeed where user must select a parent first,
        and that selection drives which object types are available.

        The web_class provides:
        - form_creation_config with:
            - parent_attribute: Name of parent field (e.g., 'server', 'edge_device')
            - intermediate_attribute: Optional intermediate selection (e.g., 'service')
            - type_classes_by_parent_class: Optional mapping parent_class → child_classes
        - get_creation_prerequisites(model_web) -> dict with:
            - parents: List of parent web objects
            - available_classes: List of all possible classes
            - intermediate_by_parent: Optional {parent_id: {items: [...], is_gpu: bool}}
            - type_classes_by_intermediate: Optional {intermediate_id: [classes]}

        Args:
            web_class: The web wrapper class
            object_type: The object type string (e.g., 'Job')

        Returns:
            Form context dictionary with parent selection fields and dynamic selects
        """
        config = web_class.form_creation_config
        prereqs = web_class.get_creation_prerequisites(self.model_web)

        parent_attr = config['parent_attribute']
        intermediate_attr = config.get('intermediate_attribute')
        parents = prereqs['parents']
        available_classes = prereqs['available_classes']

        # Build helper fields
        helper_fields = [self._build_parent_select_field(parent_attr, parents)]

        if intermediate_attr:
            helper_fields.append(self._build_intermediate_select_field(intermediate_attr))

        # Build dynamic selects
        dynamic_selects = []

        if intermediate_attr:
            # With intermediate: parent → intermediate → type
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
            "header": f"{FORM_TYPE_OBJECT[object_type]['label']} creation helper",
            "fields": helper_fields
        }
        form_sections = [helper_section] + form_sections

        if dynamic_selects:
            dynamic_form_data["dynamic_selects"] = dynamic_selects

        return {
            "form_sections": form_sections,
            "dynamic_form_data": dynamic_form_data,
            "object_type": object_type,
            "obj_formatting_data": FORM_TYPE_OBJECT[object_type],
            "header_name": f"Add new {FORM_TYPE_OBJECT[object_type]['label'].lower()}"
        }

    def _build_parent_select_field(self, parent_attr: str, parents: list) -> dict:
        """Build a select field for parent selection."""
        return {
            "input_type": "select_object",
            "web_id": parent_attr,
            "name": parent_attr.replace('_', ' ').title(),
            "options": [{"label": p.name, "value": p.efootprint_id} for p in parents],
            "label": f"Choose a {parent_attr.replace('_', ' ')}",
        }

    def _build_intermediate_select_field(self, intermediate_attr: str) -> dict:
        """Build a select field for intermediate selection (options filled dynamically)."""
        return {
            "input_type": "select_object",
            "web_id": intermediate_attr,
            "name": intermediate_attr.replace('_', ' ').title(),
            "options": None,  # Filled by dynamic select
            "label": f"{intermediate_attr.replace('_', ' ').title()} used",
        }

    def _build_intermediate_dynamic_selects(
        self, prereqs: dict, parent_attr: str, intermediate_attr: str
    ) -> list:
        """Build dynamic selects for intermediate pattern (parent → intermediate → type)."""
        intermediate_by_parent = prereqs['intermediate_by_parent']
        type_classes_by_intermediate = prereqs.get('type_classes_by_intermediate', {})

        # First select: parent → intermediate options
        intermediate_options_by_parent = {}
        # Second select: intermediate → type options
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
                    {"label": FORM_TYPE_OBJECT[cls.__name__]["label"], "value": cls.__name__}
                    for cls in extra['type_classes']
                ]

            intermediate_options_by_parent[parent_id] = options

        # Build type options for regular intermediate items
        for intermediate_id, classes in type_classes_by_intermediate.items():
            type_options_by_intermediate[intermediate_id] = [
                {"label": FORM_TYPE_OBJECT[cls.__name__]["label"], "value": cls.__name__}
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
                {"label": FORM_TYPE_OBJECT[cls.__name__]["label"], "value": cls.__name__}
                for cls in classes
            ]
        return {"input_id": "type_object_available", "filter_by": parent_attr, "list_value": type_options_by_parent}

    def _build_nested_parent_selection_creation_context(
        self,
        web_class: Type["ModelingObjectWeb"],
        object_type: str,
        efootprint_id_of_parent_to_link_to: str
    ) -> dict:
        """Build context for child object with parent known but needing internal selection (Pattern 5).

        Used by RecurrentEdgeComponentNeed where parent (RecurrentEdgeDeviceNeed) is known,
        but user must still select an edge component from the parent's device.

        The web_class must provide this method:
        - get_form_creation_data(model_web, parent_id) -> dict with:
            - 'available_classes': List of efootprint classes
            - 'helper_fields': List of field dicts for component selection
            - 'parent_context_key': Key for storing parent in context
            - 'parent': The parent object to store
            - 'extra_dynamic_data': Optional dict to merge into dynamic_form_data

        Args:
            web_class: The web wrapper class
            object_type: The object type string (e.g., 'RecurrentEdgeComponentNeed')
            efootprint_id_of_parent_to_link_to: Parent object ID

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

    def _apply_field_defaults(self, form_sections: list, field_defaults: dict) -> None:
        """Apply field default values based on config.

        Args:
            form_sections: List of form sections to modify in place
            field_defaults: Dict mapping field names to default config:
                - 'default_by_label': Set selected value by matching option label
        """
        for section in form_sections:
            for field in section.get('fields', []):
                attr_name = field.get('attr_name')
                if attr_name in field_defaults:
                    default_config = field_defaults[attr_name]
                    if 'default_by_label' in default_config:
                        label_to_find = default_config['default_by_label']
                        for option in field.get('options', []):
                            if option.get('label') == label_to_find:
                                field['selected'] = option['value']
                                break

    def _apply_field_transforms(self, form_sections: list, field_transforms: dict) -> None:
        """Apply field transformations to form sections based on config.

        Args:
            form_sections: List of form sections to modify in place
            field_transforms: Dict mapping field names to transform config:
                - 'multiselect_to_single': Convert multiselect list to single select
        """
        for section in form_sections:
            self._apply_field_transforms_to_fields(section.get('fields', []), field_transforms)

    def _apply_field_transforms_to_fields(self, fields: list, field_transforms: dict) -> None:
        """Apply field transformations to a list of fields.

        Args:
            fields: List of field dicts to modify in place
            field_transforms: Dict mapping field names to transform config
        """
        for field in fields:
            attr_name = field.get('attr_name')
            if attr_name in field_transforms:
                transform_config = field_transforms[attr_name]
                if transform_config.get('multiselect_to_single'):
                    self._convert_multiselect_to_single(field)

    def _convert_multiselect_to_single(self, field: dict) -> None:
        """Convert a multiselect field to a single select field.

        Takes options from 'unselected' (for creation) or combines
        'selected' + 'unselected' (for edition).
        """
        if 'unselected' in field:
            # Creation context: use unselected options
            options = field.get('unselected', [])
            field.update({
                'input_type': 'select_object',
                'options': options,
                'selected': options[0]['value'] if options else None
            })
            field.pop('unselected', None)
            field.pop('selected_objs', None)  # Remove if present
        elif 'selected' in field and isinstance(field.get('selected'), list):
            # Edition context: combine selected + unselected
            selected = field.get('selected', [])
            unselected = field.get('unselected', [])
            options = selected + unselected
            field.update({
                'input_type': 'select_object',
                'options': options,
                'selected': selected[0]['value'] if selected else (options[0]['value'] if options else None)
            })
            field.pop('unselected', None)
