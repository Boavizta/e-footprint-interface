import json
import os
from urllib.parse import urlencode

from django.shortcuts import render
from efootprint import __version__ as efootprint_version

from e_footprint_interface import __version__ as interface_version

GITHUB_NEW_ISSUE_URL = "https://github.com/Boavizta/e-footprint-interface/issues/new"


def build_report_bug_url(error=None):
    """Build a GitHub "new issue" URL with a prefilled bug-report template.

    The body never includes a traceback or model data (it would leak into the URL and the
    public issue); it only carries the versions and the exception type, and asks the user to
    attach the model they downloaded from the recovery page.
    """
    body_lines = [
        "## What happened",
        "<!-- What were you doing when the error occurred? -->",
        "",
        "## Model file",
        "<!-- Please drag-and-drop the model you downloaded from the recovery page here. -->",
        "",
        "## Environment",
        f"- e-footprint version: {efootprint_version}",
        f"- interface version: {interface_version}",
    ]
    if error is not None:
        body_lines.append(f"- Error: {type(error).__name__}: {error}")
    query = urlencode({"title": "[Bug] e-footprint interface error", "body": "\n".join(body_lines)})
    return f"{GITHUB_NEW_ISSUE_URL}?{query}"


def render_recovery_page(request, error=None, status=200):
    """Render the self-contained recovery page (reset / download / report a bug).

    Used as the escape hatch from a dead state: the entry view falls back to it when the
    session model fails to deserialize, and the project-wide handler500 renders it in
    production. It must never depend on the (possibly corrupt) model — it only reads whether
    raw session data exists, defensively, so the download button can be offered.
    """
    has_saved_model = False
    try:
        from model_builder.adapters.repositories import SessionSystemRepository
        has_saved_model = SessionSystemRepository(request.session).has_system_data()
    except Exception:
        pass

    context = {
        "report_bug_url": build_report_bug_url(error),
        "has_saved_model": has_saved_model,
        "error_type": type(error).__name__ if error is not None else None,
    }

    return render(request, "model_builder/recovery.html", context, status=status)


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
