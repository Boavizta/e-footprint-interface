from django.shortcuts import render

from model_builder.class_structure import generate_object_edition_structure
from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm
from model_builder.model_web import ATTRIBUTES_TO_SKIP_IN_FORMS
from model_builder.modeling_objects_web import ModelingObjectWeb


def generate_usage_pattern_edit_panel_http_response(
    request, obj_to_edit: ModelingObjectWeb, form_fields: dict, object_belongs_to_computable_system: bool):
    attributes_to_skip = [
            "start_date", "modeling_duration_value", "modeling_duration_unit", "initial_usage_journey_volume",
            "initial_usage_journey_volume_timespan", "net_growth_rate_in_percentage", "net_growth_rate_timespan"]
    form_fields = [field for field in form_fields["fields"] if field["name"] not in attributes_to_skip]

    dynamic_select_options = {
        str(conditional_value): [str(possible_value) for possible_value in possible_values]
        for conditional_value, possible_values in
        UsagePatternFromForm.conditional_list_values()["net_growth_rate_timespan"]["conditional_list_values"].items()
    }
    dynamic_select = {
        "input_id": "net_growth_rate_timespan",
        "filter_by": "initial_usage_journey_volume_timespan",
        "list_value": {
            key: [{"label": {"day": "Daily", "month": "Monthly", "year": "Yearly"}[elt], "value": elt} for elt in value]
            for key, value in dynamic_select_options.items()
        }
    }

    for field in form_fields:
        if field["name"] == "devices":
            field["input_type"] = "select"

    http_response = render(
        request, "model_builder/side_panels/usage_pattern/usage_pattern_edit.html",
        {
            "object_to_edit": obj_to_edit,
            "form_fields": form_fields,
            "object_to_edit_type": 'UsagePattern',
            "dynamic_form_data": {"dynamic_selects": [dynamic_select]},
            "object_belongs_to_computable_system": object_belongs_to_computable_system,
            "header_name": f"Edit {obj_to_edit.name}"
        }
    )

    return http_response


def generate_server_edit_panel_http_response(
    request, structure_dict: dict, obj_to_edit: ModelingObjectWeb, object_belongs_to_computable_system: bool,
    dynamic_form_data: dict):
    storage_to_edit = obj_to_edit.storage
    structure_dict["modeling_obj_attributes"] = []
    storage_structure_dict, storage_dynamic_form_data = generate_object_edition_structure(
        storage_to_edit, attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS)

    http_response = render(
        request,
        "model_builder/side_panels/server/server_edit.html",
        context={
            "object_to_edit": obj_to_edit,
            "structure_dict": structure_dict,
            "dynamic_form_data": dynamic_form_data,
            "storage_to_edit": storage_to_edit,
            "storage_structure_dict": storage_structure_dict,
            "storage_dynamic_form_data": storage_dynamic_form_data,
            "object_to_edit_type": 'Server',
            "object_belongs_to_computable_system": object_belongs_to_computable_system,
            "header_name": f"Edit {obj_to_edit.name}"
        })

    return http_response


def generate_service_edit_panel_http_response(
    request, structure_dict: dict, obj_to_edit: ModelingObjectWeb, object_belongs_to_computable_system: bool,
    dynamic_form_data: dict):
    structure_dict["modeling_obj_attributes"] = []

    return generate_generic_edit_panel_http_response(
        request, structure_dict, obj_to_edit, object_belongs_to_computable_system, dynamic_form_data)


def generate_generic_edit_panel_http_response(
    request, structure_dict: dict, obj_to_edit: ModelingObjectWeb, object_belongs_to_computable_system: bool,
    dynamic_form_data: dict):
    http_response = render(
        request,
        "model_builder/side_panels/edit/edit_panel__generic.html",
        context={
            "object_to_edit": obj_to_edit,
            "structure_dict": structure_dict,
            "dynamic_form_data": dynamic_form_data,
            "object_belongs_to_computable_system": object_belongs_to_computable_system,
            "header_name": f"Edit {obj_to_edit.name}"
        })

    return http_response
