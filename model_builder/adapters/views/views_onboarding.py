"""Onboarding adapters: the first-run template picker and template loading.

Thin HTTP adapters over the template-catalog domain service. Both render the
full builder page (target ``#main-content-block``) so the picker and the loaded
model land with the app chrome intact and the model preserved in the session —
no separate partial-swap container to keep in sync.
"""
from django.http import Http404
from django.views.decorators.http import require_POST

from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.views.views import load_system_into_session, render_model_builder
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.services import SCRATCH_ID, get_template_system_data


def open_template_picker(request):
    """Re-open the picker over the current model (help menu, home "Browse templates")."""
    repository = SessionSystemRepository(request.session)
    model_web = ModelWeb(repository)
    if model_web.system_data is None:
        # A cold visitor arriving via the home CTA has no session model yet; seed the empty
        # baseline so the canvas behind the picker renders.
        model_web = load_system_into_session(repository, get_template_system_data(SCRATCH_ID))
    return render_model_builder(request, model_web, show_template_picker=True)


@require_POST
def load_template(request, template_id):
    """Load the chosen (or scratch) system into the session and land on the canvas.

    POST-only: it replaces the session model, so it must not be reachable by a bare GET.
    The picker cards confirm first when the current model is non-empty.
    """
    repository = SessionSystemRepository(request.session)
    try:
        raw_system_data = get_template_system_data(template_id)
    except KeyError:
        raise Http404(f"Unknown template: {template_id!r}")
    model_web = load_system_into_session(repository, raw_system_data)
    return render_model_builder(request, model_web, show_template_picker=False)
