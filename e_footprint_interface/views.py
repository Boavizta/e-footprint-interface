from django.shortcuts import render

from utils import htmx_render


def home(request):
    return htmx_render(request, "home.html")


def design_catalogue(request):
    """Live design catalogue (tokens + real components) for contributors.

    Reachable only by direct navigation to /design — there is intentionally NO nav
    link anywhere (contributor-facing, communicated out of band). It renders the real
    component partials with small sample context so the catalogue can't drift from
    what ships, and it loads the app's own compiled CSS so the tokens are the real
    values. The narrative user-journey docs live in `specs/design/` in the repo.
    """
    # Minimal sample context for the partials that key off a model's creation
    # constraints (the Results bar). Plain dicts are enough — the templates only read
    # `.creation_constraints | get_item:"__results__"` then `.enabled` / `.reason`.
    results_enabled = {"creation_constraints": {"__results__": {"enabled": True, "reason": ""}}}
    results_locked = {"creation_constraints": {"__results__": {"enabled": False, "reason": (
        "No impact could be computed because the modeling is incomplete. Please make "
        "sure you have at least one usage pattern or one edge usage pattern."
    )}}}
    return render(request, "design/catalogue.html", {
        "results_enabled": results_enabled,
        "results_locked": results_locked,
    })


def server_error(request, *args, **kwargs):
    """Project-wide handler500 (production only): show the recovery page instead of a bare 500."""
    from model_builder.adapters.views.exception_handling import render_recovery_page
    return render_recovery_page(request, status=500)
