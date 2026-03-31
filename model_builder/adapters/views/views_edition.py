import json

from django.http import HttpResponse
from django.shortcuts import render
from efootprint.utils.tools import time_it

from model_builder.adapters.forms.form_context_builder import FormContextBuilder
from model_builder.adapters.forms.form_data_parser import parse_form_data, parse_form_data
from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.presenters import HtmxPresenter
from model_builder.application.use_cases import EditObjectUseCase, EditObjectInput
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.object_factory import edit_object_from_parsed_data
from model_builder.adapters.views.exception_handling import render_exception_modal_if_error


@time_it
def open_edit_object_panel(request, object_id):
    model_web = ModelWeb(SessionSystemRepository(request.session))
    obj_to_edit = model_web.get_web_object_from_efootprint_id(object_id)

    form_builder = FormContextBuilder(model_web)
    context_data = form_builder.build_edition_context(obj_to_edit)

    object_belongs_to_computable_system = (
        (len(model_web.system.servers) > 0 or len(model_web.system.external_apis) > 0
         or len(model_web.system.edge_devices) > 0) and (len(obj_to_edit.systems) > 0))
    context_data['object_belongs_to_computable_system'] = object_belongs_to_computable_system

    http_response = render(
        request, f"model_builder/side_panels/edit/{obj_to_edit.edit_template}", context=context_data)

    http_response["HX-Trigger-After-Settle"] = json.dumps({
        "initDynamicForm" : "",
        "highlightOpenedObjects": [f"button-{mirrored_card.web_id}" for mirrored_card in obj_to_edit.mirrored_cards]
        if len(obj_to_edit.mirrored_cards) > 1 else [],
    })

    return http_response


@render_exception_modal_if_error
@time_it
def edit_object(request, object_id, trigger_result_display=False):
    repository = SessionSystemRepository(request.session)

    # 1. Get object type for parsing (adapter responsibility)
    model_web = ModelWeb(repository)
    obj_to_edit = model_web.get_web_object_from_efootprint_id(object_id)
    object_type = obj_to_edit.class_as_simple_str

    # 2. Parse form data (adapter responsibility - before use case)
    parsed_form_data = parse_form_data(request.POST, object_type)

    # 3. Map request to use case input (with parsed data)
    input_data = EditObjectInput(
        object_id=object_id,
        form_data=parsed_form_data
    )

    # 4. Execute use case
    use_case = EditObjectUseCase(model_web)
    output = use_case.execute(input_data)

    # 5. Present result (with optional recomputation)
    recompute = bool(request.POST.get("recomputation", False))
    presenter = HtmxPresenter(request, model_web)
    return presenter.present_edited_object(output, recompute=recompute, trigger_result_display=trigger_result_display)


@render_exception_modal_if_error
@time_it
def open_link_existing_panel(request, parent_id, child_type_str):
    from typing import get_args
    from efootprint.utils.tools import get_init_signature_params
    from model_builder.adapters.ui_config.class_ui_config_provider import ClassUIConfigProvider
    from model_builder.adapters.forms.form_field_generator import generate_select_multiple_field

    model_web = ModelWeb(SessionSystemRepository(request.session))
    parent_obj = model_web.get_web_object_from_efootprint_id(parent_id)

    init_sig = get_init_signature_params(parent_obj.efootprint_class)
    attr_name = next(
        attr for attr in parent_obj.list_attr_names
        if get_args(init_sig[attr].annotation)[0].__name__ == child_type_str
    )

    currently_linked = getattr(parent_obj._modeling_obj, attr_name, []) or []

    field = generate_select_multiple_field(
        attr_name, parent_obj.class_as_simple_str, currently_linked, child_type_str, model_web)

    context = {
        "header_name": f"Link existing {ClassUIConfigProvider.get_label(child_type_str).lower()} to {parent_obj.name}",
        "parent_id": parent_id,
        "field": field,
    }

    http_response = render(request, "model_builder/side_panels/link/link_existing_panel.html", context=context)
    http_response["HX-Trigger-After-Settle"] = "initDynamicForm"
    return http_response


def open_panel_system_name(request):
    repository = SessionSystemRepository(request.session)
    system_data = repository.get_system_data()
    return render(request, "model_builder/side_panels/rename_system.html",context={
        "header_name": "Rename your model",
        "system_name": next(iter(system_data["System"].values()))["name"],
    })


def save_system_name(request):
    model_web = ModelWeb(SessionSystemRepository(request.session))
    parsed_data = parse_form_data(request.POST, "System")
    edited_obj, *_ = edit_object_from_parsed_data(parsed_data, model_web.system, update_system_data=True)
    return HttpResponse(edited_obj.name)
