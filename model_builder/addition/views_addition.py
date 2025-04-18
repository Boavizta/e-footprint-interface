from model_builder.addition.add_object_http_response_generators import add_new_usage_journey, add_new_usage_journey_step, \
    add_new_server, add_new_service, add_new_job, add_new_usage_pattern
from model_builder.addition.add_panel_http_response_generators import generate_generic_add_panel_http_response, \
    generate_server_add_panel_http_response, generate_service_add_panel_http_response, \
    generate_job_add_panel_http_response, generate_usage_pattern_add_panel_http_response
from model_builder.model_web import ModelWeb
from model_builder.object_creation_and_edition_utils import render_exception_modal


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


def add_object(request, object_type):
    try:
        model_web = ModelWeb(request.session)

        if object_type == "UsageJourneyStep":
            return add_new_usage_journey_step(request, model_web)
        elif object_type == "UsageJourney":
            return add_new_usage_journey(request, model_web)
        elif object_type == "ServerBase":
            return add_new_server(request, model_web)
        elif object_type == "Service":
            return add_new_service(request, model_web)
        elif object_type == "Job":
            return add_new_job(request, model_web)
        elif object_type == "UsagePatternFromForm":
            return add_new_usage_pattern(request, model_web)
        else:
            return None
    except Exception as e:
        return render_exception_modal(request, e)
