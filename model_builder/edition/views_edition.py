import json

from django.http import HttpResponse
from efootprint.builders.services.service_base_class import Service
from efootprint.core.hardware.server_base import ServerBase

from model_builder.class_structure import generate_object_edition_structure
from model_builder.edition.edit_object_http_response_generator import compute_edit_object_html_and_event_response, \
    generate_http_response_from_edit_html_and_events
from model_builder.edition.edit_panel_http_response_generators import generate_usage_pattern_edit_panel_http_response, \
    generate_server_edit_panel_http_response, generate_service_edit_panel_http_response, \
    generate_generic_edit_panel_http_response
from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm
from model_builder.model_web import ModelWeb, ATTRIBUTES_TO_SKIP_IN_FORMS
from model_builder.object_creation_and_edition_utils import edit_object_in_system, render_exception_modal


def open_edit_object_panel(request, object_id):
    model_web = ModelWeb(request.session)
    obj_to_edit = model_web.get_web_object_from_efootprint_id(object_id)

    structure_dict, dynamic_form_data = generate_object_edition_structure(
        obj_to_edit, attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS)

    object_belongs_to_computable_system = False
    if (len(model_web.system.servers) > 0) and (len(obj_to_edit.systems) > 0):
        object_belongs_to_computable_system = True

    if issubclass(obj_to_edit.efootprint_class, UsagePatternFromForm):
        http_response = generate_usage_pattern_edit_panel_http_response(
            request, model_web, obj_to_edit, object_belongs_to_computable_system, dynamic_form_data)
    elif issubclass(obj_to_edit.efootprint_class, ServerBase):
        http_response = generate_server_edit_panel_http_response(
            request, structure_dict, obj_to_edit, object_belongs_to_computable_system, dynamic_form_data)
    elif issubclass(obj_to_edit.efootprint_class, Service):
        http_response = generate_service_edit_panel_http_response(
            request, structure_dict, obj_to_edit, object_belongs_to_computable_system, dynamic_form_data)
    else:
        http_response = generate_generic_edit_panel_http_response(
            request, structure_dict, obj_to_edit, object_belongs_to_computable_system, dynamic_form_data)

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response


def edit_object(request, object_id, model_web=None):
    try:
        if model_web is None:
            model_web = ModelWeb(request.session)
        obj_to_edit = model_web.get_web_object_from_efootprint_id(object_id)
        if issubclass(obj_to_edit.efootprint_class, ServerBase):
            storage_data = json.loads(request.POST.get('storage_form_data'))
            storage = model_web.get_web_object_from_efootprint_id(storage_data["storage_id"])
            edit_object_in_system(storage_data, storage)
        response_html, ids_of_web_elements_with_lines_to_remove, data_attribute_updates, top_parent_ids = (
            compute_edit_object_html_and_event_response(request.POST, obj_to_edit))
    except Exception as e:
        return render_exception_modal(request, e)

    return generate_http_response_from_edit_html_and_events(
        response_html, ids_of_web_elements_with_lines_to_remove, data_attribute_updates, top_parent_ids)


def save_model_name(request):
    if request.method == "POST":
        model_web = ModelWeb(request.session)
        obj_to_edit = model_web.system
        edited_obj = edit_object_in_system(request.POST, obj_to_edit)
        return HttpResponse(status=204)
    else:
        return HttpResponse(status=400)
