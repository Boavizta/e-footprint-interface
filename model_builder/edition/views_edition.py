import json

from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.hardware.server_base import ServerBase
from efootprint.utils.tools import time_it

from model_builder.edition.edit_object_http_response_generator import compute_edit_object_html_and_event_response, \
    generate_http_response_from_edit_html_and_events
from model_builder.edition.edit_panel_http_response_generators import generate_usage_pattern_edit_panel_http_response, \
    generate_server_edit_panel_http_response
from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm
from model_builder.web_core.model_web import ModelWeb
from model_builder.object_creation_and_edition_utils import edit_object_in_system, render_exception_modal_if_error

@time_it
def open_edit_object_panel(request, object_id):
    model_web = ModelWeb(request.session)
    obj_to_edit = model_web.get_web_object_from_efootprint_id(object_id)

    context_data = obj_to_edit.generate_object_edition_structure()

    object_belongs_to_computable_system = False
    if (len(model_web.system.servers) > 0 or len(model_web.edge_devices) > 0) and (len(obj_to_edit.systems) > 0):
        object_belongs_to_computable_system = True
    context_data['object_belongs_to_computable_system'] = object_belongs_to_computable_system

    elif issubclass(obj_to_edit.efootprint_class, ServerBase) or issubclass(obj_to_edit.efootprint_class, EdgeDevice):
        http_response = generate_server_edit_panel_http_response(
            request, form_fields, form_fields_advanced, obj_to_edit, object_belongs_to_computable_system,
            dynamic_form_data)

    http_response = render(
        request, f"model_builder/side_panels/edit/{obj_to_edit.edit_template}.html", context=context_data)

    http_response["HX-Trigger-After-Swap"] = json.dumps({
        "initDynamicForm" : "",
        "highlightOpenedObjects": [f"button-{mirrored_card.web_id}" for mirrored_card in obj_to_edit.mirrored_cards]
        if len(obj_to_edit.mirrored_cards) > 1 else [],
    })

    return http_response


@render_exception_modal_if_error
def edit_object(request, object_id, trigger_result_display=False):
    recompute_modeling = request.POST.get("recomputation", False)
    model_web = ModelWeb(request.session)
    obj_to_edit = model_web.get_web_object_from_efootprint_id(object_id)
    if issubclass(obj_to_edit.efootprint_class, ServerBase) or issubclass(obj_to_edit.efootprint_class, EdgeDevice):
        storage_data = json.loads(request.POST.get("storage_form_data"))
        storage = model_web.get_web_object_from_efootprint_id(storage_data["storage_id"])
        edit_object_in_system(storage_data, storage)

    response_html = compute_edit_object_html_and_event_response(request.POST, obj_to_edit)

    if recompute_modeling:
        refresh_content_response = render_to_string(
            "model_builder/result/result_panel.html", context={"model_web": model_web})
        response_html += (f"<div id='result-block' hx-swap-oob='innerHTML:#result-block'>"
                         f"{refresh_content_response}</div>")
        trigger_result_display = True

    toast_and_highlight_data = {
        "ids": [mirrored_card.web_id for mirrored_card in obj_to_edit.mirrored_cards],
        "name": obj_to_edit.name,
        "action_type": "edit_object"
    }

    return generate_http_response_from_edit_html_and_events(
        response_html, toast_and_highlight_data, trigger_result_display)


def open_panel_system_name(request):
    return render(request, "model_builder/side_panels/rename_system.html",context={
        "header_name": "Rename your model",
        "system_name": next(iter(request.session["system_data"]["System"].values()))["name"],
    })


def save_system_name(request):
    edited_obj = edit_object_in_system(request.POST, ModelWeb(request.session).system)
    return HttpResponse(edited_obj.name)
