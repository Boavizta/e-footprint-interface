from django.shortcuts import render
from django.template.loader import render_to_string

from model_builder.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING
from model_builder.web_core.model_web import ModelWeb
from model_builder.object_creation_and_edition_utils import render_exception_modal_if_error


@render_exception_modal_if_error
def open_create_object_panel(request, object_type):
    model_web = ModelWeb(request.session)
    efootprint_class_web = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING[object_type]
    efootprint_id_of_parent_to_link_to = request.GET.get("efootprint_id_of_parent_to_link_to", None)
    context_data = efootprint_class_web.generate_object_creation_context(model_web, efootprint_id_of_parent_to_link_to)
    if efootprint_id_of_parent_to_link_to:
        context_data["efootprint_id_of_parent_to_link_to"] = efootprint_id_of_parent_to_link_to

    http_response = render(
        request, f"model_builder/side_panels/add/{efootprint_class_web.add_template}", context=context_data)

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response


@render_exception_modal_if_error
def add_object(request, object_type):
    model_web = ModelWeb(request.session)

    object_web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING[object_type]
    http_response =  object_web_class.add_new_object_and_return_html_response(request, model_web, object_type)

    recompute_modeling = request.POST.get("recomputation", False)
    if recompute_modeling:
        refresh_content_response = render_to_string(
            "model_builder/result/result_panel.html", context={"model_web": model_web})
        http_response.content += (f"<div id='result-block' hx-swap-oob='innerHTML:#result-block'>"
                         f"{refresh_content_response}</div>").encode('utf-8')

    return http_response
