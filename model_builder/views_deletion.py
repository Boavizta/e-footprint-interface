import json

from model_builder.web_core.model_web import ModelWeb
from model_builder.object_creation_and_edition_utils import render_exception_modal_if_error


def ask_delete_object(request, object_id):
    model_web = ModelWeb(request.session)
    web_obj = model_web.get_web_object_from_efootprint_id(object_id)

    http_response = web_obj.generate_ask_delete_http_response(request)
    http_response["HX-Trigger-After-Swap"] = json.dumps({"openModalDialog": {"modal_id": "model-builder-modal"}})

    return http_response


@render_exception_modal_if_error
def delete_object(request, object_id):
    model_web = ModelWeb(request.session)
    web_obj = model_web.get_web_object_from_efootprint_id(object_id)

    http_response = web_obj.generate_delete_http_response(request)

    return http_response
