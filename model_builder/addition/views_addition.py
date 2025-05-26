from django.template.loader import render_to_string

from model_builder.addition.add_object_http_response_generators import add_new_usage_journey, add_new_usage_journey_step, \
    add_new_server, add_new_service, add_new_job, add_new_usage_pattern
from model_builder.addition.add_panel_http_response_generators import generate_generic_add_panel_http_response, \
    generate_server_add_panel_http_response, generate_service_add_panel_http_response, \
    generate_job_add_panel_http_response, generate_usage_pattern_add_panel_http_response
from model_builder.model_web import ModelWeb
from model_builder.object_creation_and_edition_utils import render_exception_modal_if_error


def open_create_object_panel(request, object_type):
    model_web = ModelWeb(request.session)
    if object_type == "ServerBase":
        http_response = generate_server_add_panel_http_response(request, model_web)
    elif object_type == "Service":
        http_response = generate_service_add_panel_http_response(request, model_web)
    elif object_type == "Job":
        http_response = generate_job_add_panel_http_response(request, model_web)
    elif object_type == "UsagePatternFromForm":
        http_response = generate_usage_pattern_add_panel_http_response(request, model_web)
    else:
        http_response = generate_generic_add_panel_http_response(request, object_type, model_web)

    return http_response


@render_exception_modal_if_error
def add_object(request, object_type):
    recompute_modeling = request.POST.get("recomputation", False)
    model_web = ModelWeb(request.session)

    http_response = None

    if object_type == "UsageJourneyStep":
        http_response =  add_new_usage_journey_step(request, model_web)
    elif object_type == "UsageJourney":
        http_response =  add_new_usage_journey(request, model_web)
    elif object_type == "ServerBase":
        http_response =  add_new_server(request, model_web)
    elif object_type == "Service":
        http_response =  add_new_service(request, model_web)
    elif object_type == "Job":
        http_response =  add_new_job(request, model_web)
    elif object_type == "UsagePatternFromForm":
        http_response =  add_new_usage_pattern(request, model_web)

    if recompute_modeling:
        refresh_content_response = render_to_string(
            "model_builder/result/result_panel.html", context={"model_web": model_web})
        http_response.content += (f"<div id='result-block' hx-swap-oob='innerHTML:#result-block'>"
                         f"{refresh_content_response}</div>").encode('utf-8')

    return http_response
