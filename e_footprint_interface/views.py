from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from utils import htmx_render


def home(request):
    return htmx_render(request, "home.html")


# Process-level memo: build the sample model once, not on every /design hit (building a
# model computes its footprint, which can be slow / hit the Boavizta API). Read-only for
# rendering, so reuse across requests is safe.
_DESIGN_SAMPLE_MODEL = {}


def _design_sample_model():
    """A real ModelWeb built from a maintained intro template via an in-memory repository.

    Reuses the onboarding catalogue's data — no bespoke fixture to keep in sync — and never
    touches the session, so /design can render the real canvas and a real edit panel from
    production code without affecting a visitor's own model.
    """
    if "model_web" not in _DESIGN_SAMPLE_MODEL:
        from model_builder.adapters.repositories import InMemorySystemRepository
        from model_builder.adapters.views.views import load_system_into_session
        from model_builder.domain.services import get_template_system_data
        _DESIGN_SAMPLE_MODEL["model_web"] = load_system_into_session(
            InMemorySystemRepository(), get_template_system_data("ecommerce"))
    return _DESIGN_SAMPLE_MODEL["model_web"]


def design_catalogue(request):
    """Live design catalogue (tokens + real components) for contributors.

    Reachable only by direct navigation to /design — there is intentionally NO nav link
    anywhere (contributor-facing, communicated out of band). It loads the app's own compiled
    CSS (so the tokens are the real values) and renders the real canvas and a real edit side
    panel from a small sample model (so the components are exactly what ships — it can't
    drift). The narrative user-journey docs live in `specs/design/` in the repo.
    """
    from model_builder.adapters.ui_config.canvas_help_info import build_canvas_class_help_info
    from model_builder.adapters.forms.form_context_builder import FormContextBuilder

    model_web = _design_sample_model()

    # A representative object for the live edit side panel — a server shows attributes,
    # calculated attributes and source/confidence. Rendered with the real form pipeline.
    sample_obj = (list(model_web.servers) or list(model_web.usage_journeys))[0]
    form_ctx = FormContextBuilder(model_web).build_edition_context(sample_obj)
    form_ctx["object_belongs_to_computable_system"] = True
    edit_panel_html = render_to_string(
        f"model_builder/side_panels/edit/{sample_obj.edit_template}", form_ctx, request=request)

    # The Results bar keys off a model's creation constraints; show both states (the sample
    # model is complete, so fake a locked one with the real validation copy).
    results_locked = {"creation_constraints": {"__results__": {"enabled": False, "reason": (
        "No impact could be computed because the modeling is incomplete. Please make "
        "sure you have at least one usage pattern or one edge usage pattern."
    )}}}
    return render(request, "design/catalogue.html", {
        "model_web": model_web,
        "class_help_info": build_canvas_class_help_info(),
        "edit_panel_html": mark_safe(edit_panel_html),
        "edit_panel_object_name": sample_obj.name,
        "results_locked": results_locked,
    })


def server_error(request, *args, **kwargs):
    """Project-wide handler500 (production only): show the recovery page instead of a bare 500."""
    from model_builder.adapters.views.exception_handling import render_recovery_page
    return render_recovery_page(request, status=500)
