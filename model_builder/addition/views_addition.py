from django.shortcuts import render
from django.template.loader import render_to_string

from model_builder.addition.add_object_http_response_generators import add_new_object, \
    add_new_object_with_storage, add_new_service, add_new_external_api
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
    recompute_modeling = request.POST.get("recomputation", False)
    model_web = ModelWeb(request.session)

    if object_type == "ServerBase":
        http_response = add_new_object_with_storage(request, model_web, storage_type="Storage")
    elif object_type == "EdgeDevice":
        http_response = add_new_object_with_storage(request, model_web, storage_type="EdgeStorage")
    elif object_type == "Service":
        http_response =  add_new_service(request, model_web)
    elif object_type == "ExternalApi":
        http_response =  add_new_external_api(request, model_web)
    else:
        http_response =  add_new_object(request, model_web, object_type)

    if recompute_modeling:
        refresh_content_response = render_to_string(
            "model_builder/result/result_panel.html", context={"model_web": model_web})
        http_response.content += (f"<div id='result-block' hx-swap-oob='innerHTML:#result-block'>"
                         f"{refresh_content_response}</div>").encode('utf-8')

    return http_response
