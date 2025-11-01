import json
import os
from datetime import datetime
from inspect import _empty as empty_annotation
from typing import List, get_origin, get_args, TYPE_CHECKING

from django.http import QueryDict
from django.shortcuts import render
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.source_objects import SourceValue, Sources, SourceObject
from efootprint.logger import logger
from efootprint.constants.units import u
from efootprint.utils.tools import get_init_signature_params

from model_builder.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT

if TYPE_CHECKING:
    from model_builder.efootprint_to_web_mapping import ModelingObjectWeb
    from model_builder.web_core.model_web import ModelWeb


def create_efootprint_obj_from_post_data(
    create_form_data: QueryDict, model_web: "ModelWeb", object_type: str) -> ModelingObject:
    new_efootprint_obj_class = MODELING_OBJECT_CLASSES_DICT[object_type]
    init_sig_params = get_init_signature_params(new_efootprint_obj_class)
    default_values = new_efootprint_obj_class.default_values

    obj_creation_kwargs = {}
    treated_form_inputs = []
    for attr_name_with_prefix in create_form_data:
        form_inputs = {}
        attr_name = attr_name_with_prefix.replace(object_type + "_", "")
        if "__" in attr_name:
            # form inputs put __ before form fields
            # Generate the form inputs
            base_form_input_key = attr_name_with_prefix.split("__")[0]
            for key in create_form_data:
                if key.startswith(f"{base_form_input_key}__"):
                    form_input_key = key.split("__")[1]
                    form_inputs[form_input_key] = create_form_data[key]
            attr_name = attr_name.split("__")[0]

        if attr_name not in init_sig_params or attr_name in treated_form_inputs:
            continue

        if form_inputs:
            treated_form_inputs.append(attr_name)

        annotation = init_sig_params[attr_name].annotation
        if annotation is empty_annotation:
            logger.warning(
                f"Attribute {attr_name} in {object_type} has no annotation so it has been set up to str by default.")
            annotation = str
        if get_origin(annotation) and get_origin(annotation) in (list, List):
            # Exclude the empty initial value that is only here to make sure that the list is not empty and thus submitted
            selected_values = [value for value in create_form_data.get(attr_name_with_prefix).split(";") if len(
                value) > 0]
            list_attribute_object_type_str = get_args(annotation)[0].__name__
            obj_creation_kwargs[attr_name] = [
                model_web.get_efootprint_object_from_efootprint_id(obj_id, list_attribute_object_type_str)
                for obj_id in selected_values]
        elif issubclass(annotation, str):
            obj_creation_kwargs[attr_name] = create_form_data[attr_name_with_prefix]
        elif issubclass(annotation, ExplainableQuantity):
            if default_values.get(attr_name).value.magnitude != float(create_form_data[attr_name_with_prefix]) :
                source = Sources.USER_DATA
            else:
                source = default_values.get(attr_name).source
            unit = create_form_data.get(f"{attr_name_with_prefix}_unit", "dimensionless")
            obj_creation_kwargs[attr_name] = SourceValue(
                float(create_form_data[attr_name_with_prefix]) * u(unit), source)
        elif issubclass(annotation, ExplainableObject) and not form_inputs:
            if create_form_data[attr_name_with_prefix] != default_values.get(attr_name).value:
                source = Sources.USER_DATA
            else :
                source = default_values.get(attr_name).source
            obj_creation_kwargs[attr_name] = SourceObject(
                create_form_data[attr_name_with_prefix], source=source)
        elif form_inputs:
            form_inputs["label"] = f"{attr_name} in {create_form_data[f"{object_type}_name"]}"
            obj_creation_kwargs[attr_name] = ExplainableObject.from_json_dict(form_inputs)
        elif issubclass(annotation, ModelingObject):
            new_mod_obj_id = create_form_data[attr_name_with_prefix]
            mod_obj_attribute_object_type_str = annotation.__name__
            obj_to_add = model_web.get_efootprint_object_from_efootprint_id(
                new_mod_obj_id, mod_obj_attribute_object_type_str)
            obj_creation_kwargs[attr_name] = obj_to_add

    new_efootprint_obj = new_efootprint_obj_class.from_defaults(**obj_creation_kwargs)

    return new_efootprint_obj


def edit_object_in_system(edit_form_data: QueryDict, obj_to_edit: "ModelingObjectWeb"):
    model_web = obj_to_edit.model_web
    object_type = obj_to_edit.class_as_simple_str

    init_sig_params = get_init_signature_params(obj_to_edit.modeling_obj)

    attr_name_new_value_check_input_validity_pairs = []
    treated_form_inputs = []
    for attr_name_with_prefix in edit_form_data.keys():
        form_inputs = {}
        attr_name = attr_name_with_prefix.replace(object_type + "_", "")

        # Check if this is a form input (contains __)
        if "__" in attr_name:
            base_form_input_key = attr_name_with_prefix.split("__")[0]
            for key in edit_form_data:
                if key.startswith(f"{base_form_input_key}__"):
                    form_input_key = key.split("__")[1]
                    form_inputs[form_input_key] = edit_form_data[key]
            attr_name = attr_name.split("__")[0]

        if attr_name not in init_sig_params or attr_name in treated_form_inputs:
            continue

        if form_inputs:
            treated_form_inputs.append(attr_name)

        annotation = init_sig_params[attr_name].annotation
        if annotation is empty_annotation:
            logger.warning(
                f"Attribute {attr_name} in {object_type} has no annotation so it has been set up to str by default.")
            annotation = str
        if get_origin(annotation) and get_origin(annotation) in (list, List):
            # Exclude the empty initial value that is only here to make sure that the list is not empty and thus submitted
            new_mod_obj_ids = [value for value in edit_form_data.get(attr_name_with_prefix).split(";") if len(
                value) > 0]
            current_mod_obj_ids = [mod_obj.efootprint_id for mod_obj in getattr(obj_to_edit, attr_name)]
            if new_mod_obj_ids == current_mod_obj_ids:
                continue
            logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
            list_attribute_object_type_str = get_args(annotation)[0].__name__
            attr_name_new_value_check_input_validity_pairs.append(
                    [attr_name,
                     [model_web.get_efootprint_object_from_efootprint_id(obj_id, list_attribute_object_type_str)
                      for obj_id in new_mod_obj_ids],
                     False])

            continue
        if issubclass(annotation, str):
            # It should only be the case for the name parameter.
            assert attr_name == "name", \
                f"Attribute {attr_name} in {object_type} is typed as str but is not name."
            # The ModelingUpdate object is not meant to handle name updates so this parameter is updated right away.
            obj_to_edit.set_efootprint_value(attr_name, edit_form_data[attr_name_with_prefix])
            continue
        if issubclass(annotation, ModelingObject):
            new_mod_obj_id = edit_form_data[attr_name_with_prefix]
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
            request_value = edit_form_data[attr_name_with_prefix]
            request_unit = edit_form_data.get(f"{attr_name_with_prefix}_unit", "dimensionless")
            new_value = SourceValue(float(request_value) * u(request_unit), Sources.USER_DATA)
            if new_value.value != current_value.value:
                logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                new_value.set_label(current_value.label)
                attr_name_new_value_check_input_validity_pairs.append([attr_name, new_value, False])
        elif issubclass(annotation, ExplainableTimezone):
            if edit_form_data[attr_name_with_prefix] != str(current_value.value):
                logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                from pytz import timezone
                new_value = ExplainableTimezone(
                    timezone(edit_form_data[attr_name_with_prefix]), label=current_value.label,
                    source=Sources.USER_DATA)
                attr_name_new_value_check_input_validity_pairs.append([attr_name, new_value, False])
        elif issubclass(annotation, ExplainableObject) and not form_inputs:
            if attr_name in obj_to_edit.list_values:
                new_value = SourceObject(edit_form_data[attr_name_with_prefix], source=Sources.USER_DATA)
                if new_value.value != current_value.value:
                    logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                    new_value.set_label(current_value.label)
                    check_input_validity = True
                    if attr_name in obj_to_edit.attributes_with_depending_values():
                        logger.info(f"Won’t check input validity for {attr_name} "
                                    f"because it has depending values: "
                                    f"{obj_to_edit.attributes_with_depending_values()[attr_name]}")
                        check_input_validity = False
                    attr_name_new_value_check_input_validity_pairs.append([attr_name, new_value, check_input_validity])
            elif attr_name in obj_to_edit.conditional_list_values:
                # Always update value for conditional str attribute to make sure that they belong to authorized values
                new_value = SourceObject(
                    edit_form_data[attr_name_with_prefix], label=current_value.label, source=Sources.USER_DATA)
                attr_name_new_value_check_input_validity_pairs.append([attr_name, new_value, False])
            elif str(current_value.value) != edit_form_data[attr_name_with_prefix]:
                logger.debug(f"{attr_name} has changed in {obj_to_edit.efootprint_id}")
                new_value = SourceObject(
                    edit_form_data[attr_name_with_prefix], label=current_value.label, source=Sources.USER_DATA)
                attr_name_new_value_check_input_validity_pairs.append([attr_name, new_value, False])
        elif form_inputs:
            form_inputs["label"] = current_value.label if hasattr(current_value, 'label') \
                else f"{attr_name} in {obj_to_edit.name}"
            new_value = ExplainableObject.from_json_dict(form_inputs)
            if new_value != current_value:
                attr_name_new_value_check_input_validity_pairs.append([attr_name, new_value, False])


    changes_list = [
        [getattr(obj_to_edit.modeling_obj, attr_name), new_value]
        for attr_name, new_value, check_input_validity in attr_name_new_value_check_input_validity_pairs]
    ModelingUpdate(changes_list, compute_previous_system_footprints=False)

    model_web.update_system_data_with_up_to_date_calculated_attributes()

    return obj_to_edit


def render_exception_modal(request, exception):
    if os.environ.get("RAISE_EXCEPTIONS"):
        raise exception
    http_response = render(request, "model_builder/modals/exception_modal.html", {
        "modal_id": "model-builder-modal", "message": exception})

    http_response["HX-Trigger-After-Swap"] = json.dumps({"openModalDialog": {"modal_id": "model-builder-modal"}})

    return http_response


def render_exception_modal_if_error(func):
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except Exception as e:
            return render_exception_modal(request, e)
    return wrapper
