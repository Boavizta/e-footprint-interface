"""Domain object factory for creating and editing efootprint objects.

This module contains the core domain logic for constructing efootprint objects
from parsed attribute data. It handles type conversion, source tracking,
and object reference resolution.

Note: This module expects pre-parsed data (clean attribute names without prefixes).
Use adapters/forms/form_data_parser.py to parse HTTP form data before calling these functions.
"""
from copy import copy, deepcopy
from inspect import _empty as empty_annotation
from typing import Any, Dict, List, get_origin, get_args, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.source_objects import SourceValue, Sources, SourceObject
from efootprint.logger import logger
from efootprint.constants.units import u
from efootprint.utils.tools import get_init_signature_params

from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT

if TYPE_CHECKING:
    from model_builder.domain.efootprint_to_web_mapping import ModelingObjectWeb
    from model_builder.domain.entities.web_core.model_web import ModelWeb


def create_efootprint_obj_from_parsed_data(
    parsed_data: Dict[str, Any], model_web: "ModelWeb", object_type: str
) -> ModelingObject:
    """Create an efootprint object from parsed attribute data.

    Args:
        parsed_data: Dict with clean attribute names (no prefixes), nested fields as dicts,
                    and optional "_units" key for unit mappings
        model_web: ModelWeb instance for resolving object references
        object_type: The efootprint class name (e.g., "Server", "Job")

    Returns:
        New efootprint ModelingObject instance
    """
    from model_builder.domain.efootprint_to_web_mapping import get_corresponding_web_class

    new_efootprint_obj_class = MODELING_OBJECT_CLASSES_DICT[object_type]
    init_sig_params = get_init_signature_params(new_efootprint_obj_class)
    corresponding_web_class = get_corresponding_web_class(new_efootprint_obj_class)

    default_values = deepcopy(new_efootprint_obj_class.default_values)
    for default_web_attr in corresponding_web_class.default_values:
        default_values[default_web_attr] = copy(corresponding_web_class.default_values[default_web_attr])

    # Extract units metadata
    units = parsed_data.get("_units", {})

    obj_creation_kwargs = {}
    for attr_name, value in parsed_data.items():
        # Skip metadata keys
        if attr_name.startswith("_"):
            continue

        if attr_name not in init_sig_params:
            continue

        annotation = init_sig_params[attr_name].annotation
        if annotation is empty_annotation:
            logger.warning(
                f"Attribute {attr_name} in {object_type} has no annotation so it has been set up to str by default.")
            annotation = str

        # Check if value is a nested field group (form_inputs)
        form_inputs = value if isinstance(value, dict) else None

        if get_origin(annotation) and get_origin(annotation) in (list, List):
            # List of ModelingObjects - value is semicolon-separated IDs
            selected_values = [v for v in str(value).split(";") if v]
            list_attribute_object_type_str = get_args(annotation)[0].__name__
            obj_creation_kwargs[attr_name] = [
                model_web.get_efootprint_object_from_efootprint_id(obj_id, list_attribute_object_type_str)
                for obj_id in selected_values
            ]
        elif issubclass(annotation, str):
            obj_creation_kwargs[attr_name] = value
        elif issubclass(annotation, ExplainableQuantity):
            default_val = default_values.get(attr_name)
            if default_val and default_val.value.magnitude != float(value):
                source = Sources.USER_DATA
            else:
                source = default_val.source if default_val else Sources.USER_DATA
            unit = units.get(attr_name, "dimensionless")
            obj_creation_kwargs[attr_name] = SourceValue(float(value) * u(unit), source)
        elif issubclass(annotation, ExplainableObject) and not form_inputs:
            default_val = default_values.get(attr_name)
            if value != default_val:
                source = Sources.USER_DATA
            else:
                source = default_val.source if default_val else Sources.USER_DATA
            obj_creation_kwargs[attr_name] = SourceObject(value, source=source)
        elif form_inputs:
            default_val = default_values.get(attr_name)
            if hasattr(default_val, "form_inputs") and form_inputs != default_val.form_inputs:
                source = Sources.USER_DATA
            else:
                source = default_val.source if default_val else Sources.USER_DATA
            json_dict = {
                "form_inputs": form_inputs,
                "label": f"{attr_name} in {parsed_data.get('name', object_type)}",
                "source": {"name": source.name, "link": source.link} if source else None
            }
            obj_creation_kwargs[attr_name] = ExplainableObject.from_json_dict(json_dict)
        elif issubclass(annotation, ModelingObject):
            mod_obj_attribute_object_type_str = annotation.__name__
            obj_to_add = model_web.get_efootprint_object_from_efootprint_id(value, mod_obj_attribute_object_type_str)
            obj_creation_kwargs[attr_name] = obj_to_add

    return new_efootprint_obj_class.from_defaults(**obj_creation_kwargs)


def edit_object_from_parsed_data(parsed_data: Dict[str, Any], obj_to_edit: "ModelingObjectWeb"):
    """Edit an efootprint object from parsed attribute data.

    Args:
        parsed_data: Dict with clean attribute names (no prefixes), nested fields as dicts,
                    and optional "_units" key for unit mappings
        obj_to_edit: The web wrapper of the object to edit

    Returns:
        The edited object
    """
    model_web = obj_to_edit.model_web
    object_type = obj_to_edit.class_as_simple_str
    init_sig_params = get_init_signature_params(obj_to_edit.modeling_obj)

    # Extract units metadata
    units = parsed_data.get("_units", {})

    attr_name_new_value_check_input_validity_pairs = []

    for attr_name, value in parsed_data.items():
        # Skip metadata keys
        if attr_name.startswith("_"):
            continue

        if attr_name not in init_sig_params:
            continue

        annotation = init_sig_params[attr_name].annotation
        if annotation is empty_annotation:
            logger.warning(
                f"Attribute {attr_name} in {object_type} has no annotation so it has been set up to str by default.")
            annotation = str

        # Check if value is a nested field group (form_inputs)
        form_inputs = value if isinstance(value, dict) else None

        if get_origin(annotation) and get_origin(annotation) in (list, List):
            new_mod_obj_ids = [v for v in str(value).split(";") if v]
            current_mod_obj_ids = [mod_obj.efootprint_id for mod_obj in getattr(obj_to_edit, attr_name)]
            if new_mod_obj_ids == current_mod_obj_ids:
                continue
            logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
            list_attribute_object_type_str = get_args(annotation)[0].__name__
            attr_name_new_value_check_input_validity_pairs.append([
                attr_name,
                [model_web.get_efootprint_object_from_efootprint_id(obj_id, list_attribute_object_type_str)
                 for obj_id in new_mod_obj_ids],
                False
            ])
            continue

        if issubclass(annotation, str):
            assert attr_name == "name", f"Attribute {attr_name} in {object_type} is typed as str but is not name."
            obj_to_edit.set_efootprint_value(attr_name, value)
            continue

        if issubclass(annotation, ModelingObject):
            new_mod_obj_id = value
            current_mod_obj_id = getattr(obj_to_edit, attr_name).efootprint_id
            if new_mod_obj_id != current_mod_obj_id:
                logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                mod_obj_attribute_object_type_str = annotation.__name__
                obj_to_add = model_web.get_efootprint_object_from_efootprint_id(
                    new_mod_obj_id, mod_obj_attribute_object_type_str)
                attr_name_new_value_check_input_validity_pairs.append([attr_name, obj_to_add, False])
            continue

        current_value = getattr(obj_to_edit, attr_name)

        if issubclass(annotation, ExplainableQuantity):
            unit = units.get(attr_name, "dimensionless")
            new_value = SourceValue(float(value) * u(unit), Sources.USER_DATA)
            if new_value.value != current_value.value:
                logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                new_value.set_label(current_value.label)
                attr_name_new_value_check_input_validity_pairs.append([attr_name, new_value, False])
        elif issubclass(annotation, ExplainableTimezone):
            if value != str(current_value.value):
                logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                from pytz import timezone
                new_value = ExplainableTimezone(timezone(value), label=current_value.label, source=Sources.USER_DATA)
                attr_name_new_value_check_input_validity_pairs.append([attr_name, new_value, False])
        elif issubclass(annotation, ExplainableObject) and not form_inputs:
            if attr_name in obj_to_edit.list_values:
                new_value = SourceObject(value, source=Sources.USER_DATA)
                if new_value.value != current_value.value:
                    logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                    new_value.set_label(current_value.label)
                    check_input_validity = True
                    if attr_name in obj_to_edit.attributes_with_depending_values():
                        logger.info(f"Won't check input validity for {attr_name} "
                                    f"because it has depending values: "
                                    f"{obj_to_edit.attributes_with_depending_values()[attr_name]}")
                        check_input_validity = False
                    attr_name_new_value_check_input_validity_pairs.append([attr_name, new_value, check_input_validity])
            elif attr_name in obj_to_edit.conditional_list_values:
                new_value = SourceObject(value, label=current_value.label, source=Sources.USER_DATA)
                attr_name_new_value_check_input_validity_pairs.append([attr_name, new_value, False])
            elif str(current_value.value) != value:
                logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                new_value = SourceObject(value, label=current_value.label, source=Sources.USER_DATA)
                attr_name_new_value_check_input_validity_pairs.append([attr_name, new_value, False])
        elif form_inputs:
            label = current_value.label if hasattr(current_value, "label") else f"{attr_name} in {obj_to_edit.name}"
            json_dict = {"form_inputs": form_inputs, "label": label, "source": {"name": "user data", "link": None}}
            new_value = ExplainableObject.from_json_dict(json_dict)
            if new_value != current_value:
                attr_name_new_value_check_input_validity_pairs.append([attr_name, new_value, False])

    changes_list = [
        [getattr(obj_to_edit.modeling_obj, attr_name), new_value]
        for attr_name, new_value, _ in attr_name_new_value_check_input_validity_pairs
    ]
    ModelingUpdate(changes_list, compute_previous_system_footprints=False)

    model_web.update_system_data_with_up_to_date_calculated_attributes()

    return obj_to_edit
