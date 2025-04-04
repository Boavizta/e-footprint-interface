import os
from inspect import signature, _empty as empty_annotation
from typing import List, get_origin, get_args

from django.http import QueryDict
from django.shortcuts import render
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue, Sources, SourceObject
from efootprint.logger import logger

from model_builder.modeling_objects_web import ModelingObjectWeb
from model_builder.model_web import ModelWeb
from model_builder.class_structure import MODELING_OBJECT_CLASSES_DICT


def create_efootprint_obj_from_post_data(create_form_data: QueryDict, model_web: ModelWeb, object_type: str):
    new_efootprint_obj_class = MODELING_OBJECT_CLASSES_DICT[object_type]
    init_sig_params = signature(new_efootprint_obj_class.__init__).parameters
    default_values = new_efootprint_obj_class.default_values()

    obj_creation_kwargs = {}
    for attr_name_with_prefix in create_form_data.keys():
        attr_name = attr_name_with_prefix.replace(object_type + "_", "")
        if attr_name not in init_sig_params:
            continue

        annotation = init_sig_params[attr_name].annotation
        if annotation is empty_annotation:
            logger.warning(
                f"Attribute {attr_name} in {object_type} has no annotation so it has been set up to str by default.")
            annotation = str
        if get_origin(annotation) and get_origin(annotation) in (list, List):
            # Exclude the empty initial value that is only here to make sure that the list is not empty and thus submitted
            selected_values = [value for value in create_form_data.getlist(attr_name_with_prefix) if len(value) > 0]
            list_attribute_object_type_str = get_args(annotation)[0].__name__
            obj_creation_kwargs[attr_name] = [
                model_web.get_efootprint_object_from_efootprint_id(obj_id, list_attribute_object_type_str)
                for obj_id in selected_values]
        elif issubclass(annotation, str):
            obj_creation_kwargs[attr_name] = create_form_data[attr_name_with_prefix]
        elif issubclass(annotation, ExplainableQuantity):
            obj_creation_kwargs[attr_name] = SourceValue(
                float(create_form_data[attr_name_with_prefix]) * default_values[attr_name].value.units)
        elif issubclass(annotation, ExplainableObject):
            obj_creation_kwargs[attr_name] = SourceObject(
                create_form_data[attr_name_with_prefix], source=Sources.USER_DATA)
        elif issubclass(annotation, ModelingObject):
            new_mod_obj_id = create_form_data[attr_name_with_prefix]
            mod_obj_attribute_object_type_str = annotation.__name__
            obj_to_add = model_web.get_efootprint_object_from_efootprint_id(
                new_mod_obj_id, mod_obj_attribute_object_type_str)
            obj_creation_kwargs[attr_name] = obj_to_add

    new_efootprint_obj = new_efootprint_obj_class.from_defaults(**obj_creation_kwargs)

    return new_efootprint_obj


def edit_object_in_system(edit_form_data: QueryDict, obj_to_edit: ModelingObjectWeb):
    model_web = obj_to_edit.model_web
    object_type = obj_to_edit.class_as_simple_str
    default_values = obj_to_edit.default_values()

    init_sig_params = signature(obj_to_edit.modeling_obj.__init__).parameters

    for attr_name_with_prefix in edit_form_data.keys():
        attr_name = attr_name_with_prefix.replace(object_type + "_", "")
        if attr_name not in init_sig_params:
            continue

        annotation = init_sig_params[attr_name].annotation
        if annotation is empty_annotation:
            logger.warning(
                f"Attribute {attr_name} in {object_type} has no annotation so it has been set up to str by default.")
            annotation = str
        if get_origin(annotation) and get_origin(annotation) in (list, List):
            # Exclude the empty initial value that is only here to make sure that the list is not empty and thus submitted
            new_mod_obj_ids = [value for value in edit_form_data.getlist(attr_name_with_prefix) if len(value) > 0]
            current_mod_obj_ids = [mod_obj.efootprint_id for mod_obj in getattr(obj_to_edit, attr_name)]
            added_mod_obj_ids = [obj_id for obj_id in new_mod_obj_ids if obj_id not in current_mod_obj_ids]
            removed_mod_obj_ids = [obj_id for obj_id in current_mod_obj_ids if obj_id not in new_mod_obj_ids]
            logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
            unchanged_mod_obj_ids = [obj_id for obj_id in current_mod_obj_ids if obj_id not in removed_mod_obj_ids]
            if new_mod_obj_ids != current_mod_obj_ids:
                list_attribute_object_type_str = get_args(annotation)[0].__name__
                obj_to_edit.set_efootprint_value(
                    attr_name,
                    [model_web.get_efootprint_object_from_efootprint_id(obj_id, list_attribute_object_type_str)
                     for obj_id in unchanged_mod_obj_ids + added_mod_obj_ids])
        elif issubclass(annotation, str):
            obj_to_edit.set_efootprint_value(attr_name, edit_form_data[attr_name_with_prefix])
        elif issubclass(annotation, ExplainableQuantity):
            request_unit = default_values[attr_name].value.units
            request_value = edit_form_data[attr_name_with_prefix]
            new_value = SourceValue(float(request_value) * request_unit, Sources.USER_DATA)
            current_value = getattr(obj_to_edit, attr_name)
            if new_value.value != current_value.value:
                logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                new_value.set_label(current_value.label)
                obj_to_edit.set_efootprint_value(attr_name, new_value)
        elif issubclass(annotation, ExplainableObject):
            if attr_name in obj_to_edit.list_values().keys():
                new_value = SourceObject(edit_form_data[attr_name_with_prefix], source=Sources.USER_DATA)
                current_value = getattr(obj_to_edit, attr_name)
                if new_value.value != current_value.value:
                    logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                    new_value.set_label(current_value.label)
                    check_input_validity = True
                    if attr_name in obj_to_edit.attributes_with_depending_values().keys():
                        logger.info(f"Won’t check input validity for {attr_name} "
                                    f"because it has depending values: "
                                    f"{obj_to_edit.attributes_with_depending_values()[attr_name]}")
                        check_input_validity = False
                    obj_to_edit.set_efootprint_value(attr_name, new_value, check_input_validity)
            else:
                new_value = SourceObject(edit_form_data[attr_name_with_prefix], source=Sources.USER_DATA)
                current_value = getattr(obj_to_edit, attr_name)
                if new_value.value != current_value.value:
                    logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                # Always update value for conditional str attribute to make sure that they belong to authorized values
                new_value.set_label(current_value.label)
                obj_to_edit.set_efootprint_value(attr_name, new_value)

        elif issubclass(annotation, ModelingObject):
            new_mod_obj_id = edit_form_data[attr_name_with_prefix]
            current_mod_obj_id = getattr(obj_to_edit, attr_name).efootprint_id
            if new_mod_obj_id != current_mod_obj_id:
                logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                mod_obj_attribute_object_type_str = annotation.__name__
                obj_to_add = model_web.get_efootprint_object_from_efootprint_id(
                    new_mod_obj_id, mod_obj_attribute_object_type_str)
                obj_to_edit.set_efootprint_value(attr_name, obj_to_add)

    # Update session data
    model_web.session["system_data"][obj_to_edit.class_as_simple_str][obj_to_edit.efootprint_id] = obj_to_edit.to_json()
    # Here we updated a sub dict of request.session so we have to explicitly tell Django that it has been updated
    model_web.session.modified = True

    return obj_to_edit


def render_exception_modal(request, exception):
    if os.environ.get("RAISE_EXCEPTIONS"):
        raise exception
    http_response = render(request, "model_builder/modals/exception_modal.html", {
        "msg": exception})

    http_response["HX-Trigger-After-Swap"] = "openModalDialog"

    return http_response
