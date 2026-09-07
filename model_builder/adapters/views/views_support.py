from django.urls import reverse

from model_builder.adapters.repositories import SessionWorkspaceRepository
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
