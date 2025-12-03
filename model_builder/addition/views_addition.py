import json

from django.shortcuts import render

from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.presenters import HtmxPresenter
from model_builder.application.use_cases import CreateObjectUseCase, CreateObjectInput
from model_builder.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING
from model_builder.web_core.model_web import ModelWeb
from model_builder.object_creation_and_edition_utils import render_exception_modal_if_error


@render_exception_modal_if_error
def open_create_object_panel(request, object_type):
    model_web = ModelWeb(SessionSystemRepository(request.session))
    efootprint_class_web = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING[object_type]
    efootprint_id_of_parent_to_link_to = request.GET.get("efootprint_id_of_parent_to_link_to", None)
    context_data = efootprint_class_web.generate_object_creation_context(
        model_web, efootprint_id_of_parent_to_link_to, object_type)
    if efootprint_id_of_parent_to_link_to:
        context_data["efootprint_id_of_parent_to_link_to"] = efootprint_id_of_parent_to_link_to

    # Add HTMX configuration from the class
    htmx_config = efootprint_class_web.get_htmx_form_config(context_data)
    # Convert hx_vals dict to JSON string for template
    if "hx_vals" in htmx_config and htmx_config["hx_vals"]:
        htmx_config["hx_vals"] = json.dumps(htmx_config["hx_vals"])
    context_data["htmx_config"] = htmx_config

    http_response = render(
        request, f"model_builder/side_panels/add/{efootprint_class_web.add_template}", context=context_data)

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response


@render_exception_modal_if_error
def add_object(request, object_type):
    repository = SessionSystemRepository(request.session)

    # 1. Map request to use case input
    input_data = CreateObjectInput(
        object_type=object_type,
        form_data=request.POST,
        parent_id=request.POST.get("efootprint_id_of_parent_to_link_to")
    )

    # 2. Execute use case
    use_case = CreateObjectUseCase(repository)
    output = use_case.execute(input_data)

    # 3. Present result (with optional recomputation)
    recompute = bool(request.POST.get("recomputation", False))
    presenter = HtmxPresenter(request)
    return presenter.present_created_object(output, recompute=recompute)
