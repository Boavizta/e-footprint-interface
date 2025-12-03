import json

from django.http import HttpResponse
from django.shortcuts import render
from efootprint.utils.tools import time_it

from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.presenters import HtmxPresenter
from model_builder.application.use_cases import EditObjectUseCase, EditObjectInput
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.object_creation_and_edition_utils import edit_object_in_system, render_exception_modal_if_error

@time_it
def open_edit_object_panel(request, object_id):
    model_web = ModelWeb(SessionSystemRepository(request.session))
    obj_to_edit = model_web.get_web_object_from_efootprint_id(object_id)

    context_data = obj_to_edit.generate_object_edition_context()

    object_belongs_to_computable_system = (
        (len(model_web.system.servers) > 0 or len(model_web.edge_devices) > 0) and (len(obj_to_edit.systems) > 0))
    context_data['object_belongs_to_computable_system'] = object_belongs_to_computable_system

    http_response = render(
        request, f"model_builder/side_panels/edit/{obj_to_edit.edit_template}", context=context_data)

    http_response["HX-Trigger-After-Swap"] = json.dumps({
        "initDynamicForm" : "",
        "highlightOpenedObjects": [f"button-{mirrored_card.web_id}" for mirrored_card in obj_to_edit.mirrored_cards]
        if len(obj_to_edit.mirrored_cards) > 1 else [],
    })

    return http_response


@render_exception_modal_if_error
def edit_object(request, object_id, trigger_result_display=False):
    repository = SessionSystemRepository(request.session)

    # 1. Map request to use case input
    input_data = EditObjectInput(
        object_id=object_id,
        form_data=request.POST
    )

    # 2. Execute use case
    use_case = EditObjectUseCase(repository)
    output = use_case.execute(input_data)

    # 3. Present result (with optional recomputation)
    recompute = bool(request.POST.get("recomputation", False))
    presenter = HtmxPresenter(request)
    return presenter.present_edited_object(output, recompute=recompute, trigger_result_display=trigger_result_display)


def open_panel_system_name(request):
    return render(request, "model_builder/side_panels/rename_system.html",context={
        "header_name": "Rename your model",
        "system_name": next(iter(request.session["system_data"]["System"].values()))["name"],
    })


def save_system_name(request):
    edited_obj = edit_object_in_system(request.POST, ModelWeb(SessionSystemRepository(request.session)).system)
    return HttpResponse(edited_obj.name)
