import os
from datetime import datetime

from django.http import QueryDict
from django.shortcuts import render
from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from efootprint.abstract_modeling_classes.source_objects import SourceValue, Sources, SourceHourlyValues, SourceObject
from efootprint.constants.units import u
from efootprint.logger import logger

from model_builder.modeling_objects_web import ModelingObjectWeb
from model_builder.model_web import ModelWeb
from model_builder.class_structure import MODELING_OBJECT_CLASSES_DICT, efootprint_class_structure


def create_efootprint_obj_from_post_data(create_form_data: QueryDict, model_web: ModelWeb, object_type: str):
    new_efootprint_obj_class = MODELING_OBJECT_CLASSES_DICT[object_type]

    obj_creation_kwargs = {}
    obj_structure = efootprint_class_structure(object_type)
    obj_creation_kwargs["name"] = create_form_data["name"]

    for attr_dict in obj_structure["numerical_attributes"]:
        attr_value_in_list = create_form_data.getlist(f'{attr_dict["attr_name"]}')
        if not attr_value_in_list:
            logger.info(f"No value for {attr_dict['attr_name']} in {object_type} form. "
                        f"Default value {new_efootprint_obj_class.default_values()[attr_dict['attr_name']]} "
                        f"will be used.")
        else:
            obj_creation_kwargs[attr_dict["attr_name"]] = SourceValue(
                float(attr_value_in_list[0]) * u(attr_dict["unit"]))

    for attr_dict in obj_structure["hourly_quantities_attributes"]:
        obj_creation_kwargs[attr_dict["attr_name"]] = SourceHourlyValues(
            # Create hourly_usage_journey_starts from request_post_data with the startDate and values
            create_hourly_usage_df_from_list(
                [float(value) for value
                 in create_form_data.getlist(f'list_{attr_dict["attr_name"]}')[0].split(",")],
                start_date=datetime.strptime(
                    create_form_data[f'date_{attr_dict["attr_name"]}'], "%Y-%m-%d"),
                pint_unit=u.dimensionless
            )
        )

    for str_attr in obj_structure["str_attributes"] + obj_structure["conditional_str_attributes"]:
        str_attr_name = str_attr["attr_name"]
        if f'{str_attr_name}' not in create_form_data.keys():
            logger.info(f"No value for {str_attr_name} in {object_type} form. "
                        f"Default value {new_efootprint_obj_class.default_values()[str_attr_name]} will be used.")
        else:
            obj_creation_kwargs[str_attr_name] = SourceObject(
                create_form_data[f'{str_attr_name}'], source=Sources.USER_DATA)

    for mod_obj in obj_structure["modeling_obj_attributes"]:
        new_mod_obj_id = create_form_data[f'{mod_obj["attr_name"]}']
        obj_to_add = model_web.get_efootprint_object_from_efootprint_id(new_mod_obj_id, mod_obj["object_type"])
        obj_creation_kwargs[mod_obj["attr_name"]] = obj_to_add

    for mod_obj in obj_structure["list_attributes"]:
        obj_creation_kwargs[mod_obj["attr_name"]] = [
            model_web.get_efootprint_object_from_efootprint_id(obj_id, mod_obj["object_type"])
            for obj_id in create_form_data.getlist(f'{mod_obj["attr_name"]}')]

    new_efootprint_obj = new_efootprint_obj_class.from_defaults(**obj_creation_kwargs)

    return new_efootprint_obj


def edit_object_in_system(edit_form_data: QueryDict, obj_to_edit: ModelingObjectWeb):
    model_web = obj_to_edit.model_web
    obj_structure = obj_to_edit.generate_structure()

    obj_to_edit.set_efootprint_value("name", edit_form_data["name"])

    for attr_dict in obj_structure["numerical_attributes"]:
        if attr_dict["attr_name"] in edit_form_data.keys():
            request_unit = attr_dict["unit"]
            request_value = edit_form_data[attr_dict["attr_name"]]
            new_value = SourceValue(float(request_value) * u(request_unit), Sources.USER_DATA)
            current_value = getattr(obj_to_edit, attr_dict["attr_name"])
            if new_value.value != current_value.value:
                logger.debug(f"{attr_dict['attr_name']} has changed in {obj_to_edit.efootprint_id}")
                new_value.set_label(current_value.label)
                obj_to_edit.set_efootprint_value(attr_dict["attr_name"], new_value)
    for attr_dict in obj_structure["hourly_quantities_attributes"]:
        if (f"list_{attr_dict["attr_name"]}" in edit_form_data.keys()
            and f"date_{attr_dict['attr_name']}" in edit_form_data.keys()):
            logger.debug(f"{attr_dict['attr_name']} has changed in {obj_to_edit.efootprint_id}")
            values = edit_form_data.getlist(f'list_{attr_dict["attr_name"]}')[0].split(",")
            start_date = datetime.strptime(edit_form_data[f'date_{attr_dict["attr_name"]}'], "%Y-%m-%d")
            new_value = SourceHourlyValues(
                create_hourly_usage_df_from_list([float(value) for value in values],
                                                 start_date=start_date, pint_unit=u.dimensionless)
            )
            current_value = getattr(obj_to_edit, attr_dict["attr_name"])
            if new_value != current_value.explainable_object:
                logger.debug(f"{attr_dict['attr_name']} has changed in {obj_to_edit.efootprint_id}")
                obj_to_edit.set_efootprint_value(attr_dict["attr_name"], new_value)
    for attr_dict in obj_structure["str_attributes"]:
        if attr_dict["attr_name"] in edit_form_data.keys():
            new_value = SourceObject(edit_form_data[attr_dict["attr_name"]], source=Sources.USER_DATA)
            current_value = getattr(obj_to_edit, attr_dict["attr_name"])
            if new_value.value != current_value.value:
                logger.debug(f"{attr_dict['attr_name']} has changed in {obj_to_edit.efootprint_id}")
                new_value.set_label(current_value.label)
                check_input_validity = True
                if attr_dict["attr_name"] in obj_to_edit.attributes_with_depending_values().keys():
                    logger.info(f"Won’t check input validity for {attr_dict['attr_name']} "
                                f"because it has depending values: "
                                f"{obj_to_edit.attributes_with_depending_values()[attr_dict['attr_name']]}")
                    check_input_validity = False
                obj_to_edit.set_efootprint_value(attr_dict["attr_name"], new_value, check_input_validity)
    for attr_dict in obj_structure["conditional_str_attributes"]:
        if attr_dict["attr_name"] in edit_form_data.keys():
            new_value = SourceObject(edit_form_data[attr_dict["attr_name"]], source=Sources.USER_DATA)
            current_value = getattr(obj_to_edit, attr_dict["attr_name"])
            if new_value.value != current_value.value:
                logger.debug(f"{attr_dict['attr_name']} has changed in {obj_to_edit.efootprint_id}")
            # Always update value for conditional str attribute to make sure that they belong to authorized values
            new_value.set_label(current_value.label)
            obj_to_edit.set_efootprint_value(attr_dict["attr_name"], new_value)
    for mod_obj in obj_structure["modeling_obj_attributes"]:
        if mod_obj["attr_name"] in edit_form_data.keys():
            new_mod_obj_id = edit_form_data[mod_obj["attr_name"]]
            current_mod_obj_id = getattr(obj_to_edit, mod_obj["attr_name"]).efootprint_id
            if new_mod_obj_id != current_mod_obj_id:
                logger.debug(f"{mod_obj['attr_name']} has changed in {obj_to_edit.efootprint_id}")
                obj_to_add = model_web.get_efootprint_object_from_efootprint_id(
                    new_mod_obj_id, mod_obj["object_type"])
                obj_to_edit.set_efootprint_value(mod_obj["attr_name"], obj_to_add)
    for mod_obj in obj_structure["list_attributes"]:
        if mod_obj["attr_name"] in edit_form_data.keys():
            new_mod_obj_ids = edit_form_data.getlist("" +mod_obj["attr_name"])
            current_mod_obj_ids = [mod_obj.efootprint_id for mod_obj in getattr(obj_to_edit, mod_obj["attr_name"])]
            added_mod_obj_ids = [obj_id for obj_id in new_mod_obj_ids if obj_id not in current_mod_obj_ids]
            removed_mod_obj_ids = [obj_id for obj_id in current_mod_obj_ids if obj_id not in new_mod_obj_ids]
            logger.debug(f"{mod_obj['attr_name']} has changed in {obj_to_edit.efootprint_id}")
            unchanged_mod_obj_ids = [obj_id for obj_id in current_mod_obj_ids if obj_id not in removed_mod_obj_ids]
            if new_mod_obj_ids != current_mod_obj_ids:
                obj_to_edit.set_efootprint_value(
                    mod_obj["attr_name"],
                    [model_web.get_efootprint_object_from_efootprint_id(obj_id, mod_obj["object_type"])
                     for obj_id in unchanged_mod_obj_ids + added_mod_obj_ids])

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
