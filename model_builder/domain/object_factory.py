"""Domain object factory for creating and editing efootprint objects.

This module contains the core domain logic for constructing efootprint objects
from parsed attribute data. It handles type conversion, source tracking,
and object reference resolution.

Note: This module expects pre-parsed data (clean attribute names without prefixes).
Use adapters/forms/form_data_parser.py to parse HTTP form data before calling these functions.
"""
from copy import copy, deepcopy
from typing import Any, Dict, List, get_origin, get_args, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.source_objects import Sources
from efootprint.logger import logger
from efootprint.utils.tools import get_init_signature_params

from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.type_annotation_utils import resolve_optional_annotation

if TYPE_CHECKING:
    from model_builder.domain.efootprint_to_web_mapping import ModelingObjectWeb
    from model_builder.domain.entities.web_core.model_web import ModelWeb


def _build_explainable_object_dict_entries(value: Dict[str, Any], model_web: "ModelWeb", attr_name: str) -> dict:
    entries = {}
    for key_id, explainable_value_dict in value.items():
        if key_id not in model_web.flat_efootprint_objs_dict:
            raise ValueError(f"Unknown modeling object id '{key_id}' in {attr_name}.")
        explainable_obj = ExplainableObject.from_json_dict(explainable_value_dict)
        explainable_obj.source = Sources.USER_DATA
        entries[model_web.flat_efootprint_objs_dict[key_id]] = explainable_obj
    return entries


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

    obj_creation_kwargs = {}

    for attr_name, value in parsed_data.items():
        if attr_name == "name":
            obj_creation_kwargs[attr_name] = value
            continue
        if attr_name not in init_sig_params:
            continue
        annotation = init_sig_params[attr_name].annotation
        annotation = resolve_optional_annotation(annotation)
        if get_origin(annotation) and get_origin(annotation) in (list, List):
            list_attribute_object_type_str = get_args(annotation)[0].__name__
            obj_creation_kwargs[attr_name] = [
                model_web.get_efootprint_object_from_efootprint_id(obj_id, list_attribute_object_type_str)
                for obj_id in value
            ]
        elif issubclass(annotation, ExplainableObjectDict):
            explainable_dict = ExplainableObjectDict()
            for key_id, explainable_value_dict in value.items():
                if key_id not in model_web.flat_efootprint_objs_dict:
                    raise ValueError(f"Unknown modeling object id '{key_id}' in {attr_name}.")
                explainable_value = ExplainableObject.from_json_dict(explainable_value_dict)
                if explainable_value.source is None:
                    explainable_value.source = Sources.USER_DATA
                explainable_dict[model_web.flat_efootprint_objs_dict[key_id]] = explainable_value
            obj_creation_kwargs[attr_name] = explainable_dict
        elif issubclass(annotation, ModelingObject):
            mod_obj_attribute_object_type_str = annotation.__name__
            obj_to_add = model_web.get_efootprint_object_from_efootprint_id(value, mod_obj_attribute_object_type_str)
            obj_creation_kwargs[attr_name] = obj_to_add
        elif issubclass(annotation, ExplainableObject):
            explainable_object = ExplainableObject.from_json_dict(value)
            if attr_name in default_values:
                default_value = default_values[attr_name]
                if (# form inputs are tested directly because default values might have missing fields
                    (hasattr(default_value, "form_inputs")
                     and default_value.form_inputs != explainable_object.form_inputs)
                    or default_values[attr_name] != explainable_object):
                    explainable_object.source = Sources.USER_DATA
            else:
                explainable_object.source = default_values[attr_name].source
            obj_creation_kwargs[attr_name] = explainable_object

    return new_efootprint_obj_class.from_defaults(**obj_creation_kwargs)


def edit_object_from_parsed_data(parsed_data: Dict[str, Any], obj_to_edit: "ModelingObjectWeb",
                                 update_system_data=False):
    """Edit an efootprint object from parsed attribute data.

    Args:
        parsed_data: Dict with clean attribute names (no prefixes), nested fields as dicts,
                    and optional "_units" key for unit mappings
        obj_to_edit: The web wrapper of the object to edit
        update_system_data: Whether to update system data after editing

    Returns:
        Tuple of (edited_object, had_non_name_changes: bool, name_changed: bool)
    """
    model_web = obj_to_edit.model_web
    init_sig_params = get_init_signature_params(obj_to_edit.efootprint_class)

    changes_list = []
    old_name = obj_to_edit.name

    for attr_name, value in parsed_data.items():
        if attr_name not in init_sig_params or attr_name == "self":
            continue
        if attr_name == "name":
            obj_to_edit.set_efootprint_value(attr_name, value)
            continue

        annotation = init_sig_params[attr_name].annotation
        annotation = resolve_optional_annotation(annotation)
        current_value = getattr(obj_to_edit.modeling_obj, attr_name)

        if get_origin(annotation) and get_origin(annotation) in (list, List):
            current_mod_obj_ids = [mod_obj.efootprint_id for mod_obj in getattr(obj_to_edit, attr_name)]
            if value == current_mod_obj_ids:
                continue
            logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
            list_attribute_object_type_str = get_args(annotation)[0].__name__
            changes_list.append([
                current_value,
                [model_web.get_efootprint_object_from_efootprint_id(obj_id, list_attribute_object_type_str)
                 for obj_id in value]])
            continue

        if issubclass(annotation, ExplainableObjectDict):
            new_entries = _build_explainable_object_dict_entries(value, model_web, attr_name)
            if new_entries != current_value:
                logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                changes_list.append([current_value, ExplainableObjectDict(new_entries)])
            continue

        if issubclass(annotation, ModelingObject):
            new_mod_obj_id = value
            current_mod_obj_id = getattr(obj_to_edit, attr_name).efootprint_id
            if new_mod_obj_id != current_mod_obj_id:
                logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                mod_obj_attribute_object_type_str = annotation.__name__
                obj_to_add = model_web.get_efootprint_object_from_efootprint_id(
                    new_mod_obj_id, mod_obj_attribute_object_type_str)
                changes_list.append([current_value, obj_to_add])
            continue

        if issubclass(annotation, ExplainableObject):
            new_value = ExplainableObject.from_json_dict(value)
            new_value.set_label(current_value.label)
            new_value.source = Sources.USER_DATA
            if new_value != current_value:
                changes_list.append([current_value, new_value])

    if changes_list:
        ModelingUpdate(changes_list, compute_previous_system_footprints=False)

    if update_system_data:
        model_web.persist_to_cache()

    return obj_to_edit, bool(changes_list), obj_to_edit.name != old_name
