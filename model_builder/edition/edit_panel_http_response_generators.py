from django.shortcuts import render

from model_builder.class_structure import generate_object_edition_structure
from model_builder.model_web import ModelWeb, default_networks, default_countries, default_devices, \
    ATTRIBUTES_TO_SKIP_IN_FORMS
from model_builder.modeling_objects_web import ModelingObjectWeb


def generate_usage_pattern_edit_panel_http_response(
    request, model_web: ModelWeb, obj_to_edit: ModelingObjectWeb, object_belongs_to_computable_system: bool,
    dynamic_form_data: dict):
    networks = [{"efootprint_id": network["id"], "name": network["name"]} for network in
                default_networks().values()]
    countries = [{"efootprint_id": country["id"], "name": country["name"]} for country in
                 default_countries().values()]
    devices = [{"efootprint_id": device["id"], "name": device["name"]} for device in default_devices().values()]
    usage_journeys = [{'efootprint_id': uj.efootprint_id, 'name': uj.name} for uj in model_web.usage_journeys]

    modeling_obj_attributes = [
        {"attr_name": "devices", "existing_objects": devices,
         "selected_efootprint_id": obj_to_edit.devices[0].efootprint_id},
        {"attr_name": "network", "existing_objects": networks,
         "selected_efootprint_id": obj_to_edit.network.efootprint_id},
        {"attr_name": "country", "existing_objects": countries,
         "selected_efootprint_id": obj_to_edit.country.efootprint_id},
        {"attr_name": "usage_journey", "existing_objects": usage_journeys,
         "selected_efootprint_id": obj_to_edit.usage_journey.efootprint_id},
    ]

    dynamic_selects = dynamic_form_data["dynamic_lists"]
    dynamic_selects[0]["list_value"] = {
        key: [{"label": {"day": "Daily", "month": "Monthly", "year": "Yearly"}[elt], "value": elt} for elt in value]
        for key, value in dynamic_selects[0]["list_value"].items()
    }

    http_response = render(
        request, "model_builder/side_panels/usage_pattern/usage_pattern_edit.html",
        {
            "modeling_obj_attributes": modeling_obj_attributes,
            "object_to_edit": obj_to_edit,
            "object_to_edit_type": 'UsagePattern',
            "dynamic_form_data": {"dynamic_selects": dynamic_selects},
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
