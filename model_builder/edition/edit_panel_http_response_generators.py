from django.shortcuts import render

from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm
from model_builder.web_abstract_modeling_classes.modeling_object_web import ATTRIBUTES_TO_SKIP_IN_FORMS
from model_builder.efootprint_to_web_mapping import ModelingObjectWeb


def generate_server_edit_panel_http_response(
    request, form_fields: dict, form_fields_advanced: dict, obj_to_edit: ModelingObjectWeb,
    object_belongs_to_computable_system: bool, dynamic_form_data: dict):
    storage_to_edit = obj_to_edit.storage
    storage_form_fields, storage_form_fields_advanced, storage_dynamic_form_data = generate_object_edition_structure(
        storage_to_edit, attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS)

    http_response = render(
        request,
        "model_builder/side_panels/server/server_edit.html",
        context={
            "object_to_edit": obj_to_edit,
            "form_fields": form_fields,
            "form_fields_advanced": form_fields_advanced,
            "dynamic_form_data": dynamic_form_data,
            "storage_to_edit": storage_to_edit,
            "storage_form_fields": storage_form_fields,
            "storage_form_fields_advanced": storage_form_fields_advanced,
            "storage_dynamic_form_data": storage_dynamic_form_data,
            "object_belongs_to_computable_system": object_belongs_to_computable_system,
            "header_name": f"Edit {obj_to_edit.name}"
        })

    return http_response


def generate_generic_edit_panel_http_response(
    request, form_fields: dict, form_fields_advanced: dict, obj_to_edit: ModelingObjectWeb,
    object_belongs_to_computable_system: bool, dynamic_form_data: dict):
    http_response = render(
        request,
        "model_builder/side_panels/edit/edit_panel__generic.html",
        context={
            "object_to_edit": obj_to_edit,
            "form_fields": form_fields,
            "form_fields_advanced": form_fields_advanced,
            "dynamic_form_data": dynamic_form_data,
            "object_belongs_to_computable_system": object_belongs_to_computable_system,
            "header_name": f"Edit {obj_to_edit.name}"
        })

    return http_response
