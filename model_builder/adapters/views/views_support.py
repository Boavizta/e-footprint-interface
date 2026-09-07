from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from model_builder.adapters.repositories import SessionWorkspaceRepository
from model_builder.adapters.repositories.cache_backend import CacheTouchOutcome
from model_builder.adapters.repositories.recovery_retention import set_recovery_retention
from model_builder.adapters.repositories.workspace_index import WorkspaceIndex
from model_builder.adapters.views.data_status import build_data_status, format_duration
from model_builder.adapters.views.exception_handling import build_feedback_email_url, build_github_feedback_url
from utils import htmx_render


def support(request):
    """Render the global feedback flow as a standalone page or builder partial."""
    workspace = SessionWorkspaceRepository(request.session)
    recovery_mode = request.GET.get("recovery") == "1"
    context = {
        "standalone": request.headers.get("HX-Request") != "true",
        "recovery_mode": recovery_mode,
        "has_saved_model": workspace.active_repository().has_system_data(),
        "download_model_url": reverse("download-raw-json" if recovery_mode else "download-json"),
        "github_bug_url": build_github_feedback_url("bug"),
        "github_feedback_url": build_github_feedback_url("feedback"),
        "email_bug_url": build_feedback_email_url("bug"),
        "email_feedback_url": build_feedback_email_url("feedback"),
    }
    return htmx_render(request, "model_builder/support.html", context)


def _data_privacy_context(request, retention_results=None):
    return {
        "standalone": request.headers.get("HX-Request") != "true",
        "data_status": build_data_status(request.session),
        "retention_results": retention_results,
    }


def _render_data_privacy(request, retention_results=None):
    return render(
        request,
        "model_builder/side_panels/data_privacy.html",
        _data_privacy_context(request, retention_results),
    )


@require_GET
def data_privacy(request):
    """Render deployment disclosures and session controls without loading either modeling."""
    return _render_data_privacy(request)


@require_POST
def update_recovery_retention(request):
    """Apply one allowlisted retention period and render the per-slot outcomes."""
    try:
        retention_seconds = int(request.POST.get("retention_seconds", ""))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("Choose one of the available recovery periods.")

    slots = WorkspaceIndex(request.session).slots()
    try:
        results = set_recovery_retention(request.session, retention_seconds)
    except ValueError:
        return HttpResponseBadRequest("Choose one of the available recovery periods.")

    if len(slots) == 1:
        role_labels = {slots[0]: "Current modeling"}
    else:
        role_labels = {
            slot: "Reference modeling" if position == 0 else "Comparison modeling"
            for position, slot in enumerate(slots)
        }
    retention_results = {
        "summary": f"Recovery retention is now {format_duration(retention_seconds)}.",
        "slots": [{"label": role_labels[slot], "outcome": outcome.value} for slot, outcome in results.items()],
        "has_errors": any(outcome is CacheTouchOutcome.ERROR for outcome in results.values()),
    }
    return _render_data_privacy(request, retention_results)
