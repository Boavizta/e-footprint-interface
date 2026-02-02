import json
import os

from django.shortcuts import render


def render_exception_modal(request, exception):
    if os.environ.get("RAISE_EXCEPTIONS"):
        raise exception
    http_response = render(request, "model_builder/modals/exception_modal.html", {
        "modal_id": "model-builder-modal", "message": exception})

    http_response["HX-Trigger-After-Settle"] = json.dumps({"openModalDialog": {"modal_id": "model-builder-modal"}})

    return http_response


def render_exception_modal_if_error(func):
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except Exception as e:
            return render_exception_modal(request, e)
    return wrapper
