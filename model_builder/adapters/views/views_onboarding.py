"""Onboarding adapters: the first-run example picker and example loading.

Thin HTTP adapters over the example-catalog domain service. Both render the
full builder page (target ``#main-content-block``) so the picker and the loaded
model land with the app chrome intact and the model preserved in the session —
no separate partial-swap container to keep in sync.
"""
import json
from pathlib import Path

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from model_builder.adapters.repositories import SessionWorkspaceRepository
from model_builder.adapters.views.views import load_system_into_session, render_model_builder
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.services import SCRATCH_ID, get_example_system_data


def open_example_picker(request):
    """Re-open the picker over the current model (help menu)."""
    workspace = SessionWorkspaceRepository(request.session)
    repository = workspace.active_repository()
    model_web = ModelWeb(repository)
    if model_web.system_data is None:
        # A cold visitor arriving via the home CTA has no session model yet; seed the empty
        # baseline so the canvas behind the picker renders.
        model_web = load_system_into_session(repository, get_example_system_data(SCRATCH_ID))
    return render_model_builder(request, model_web, show_example_picker=True, workspace=workspace)


@require_POST
def load_example(request, example_id):
    """Load the chosen (or scratch) system into the session and land on the canvas.

    POST-only: it replaces the session model, so it must not be reachable by a bare GET.
    The picker cards confirm first when the current model is non-empty.
    """
    workspace = SessionWorkspaceRepository(request.session)
    repository = workspace.active_repository()
    try:
        raw_system_data = get_example_system_data(example_id)
    except KeyError:
        raise Http404(f"Unknown example: {example_id!r}")
    model_web = load_system_into_session(repository, raw_system_data, workspace=workspace)
    return render_model_builder(request, model_web, show_example_picker=False, workspace=workspace)


def load_example_deeplink(request, example_id):
    """Shareable GET deep link behind the docs' "Load this scenario" links.

    Loads the named scenario into the session and redirects to the canvas so the URL
    settles on ``/model_builder/``. The link click is itself the user's explicit intent
    to load (and a bare GET cannot run the picker's client-side replace-confirm), so it
    loads directly; an unknown id 404s like any other bad URL.
    """
    workspace = SessionWorkspaceRepository(request.session)
    repository = workspace.active_repository()
    try:
        raw_system_data = get_example_system_data(example_id)
    except KeyError:
        raise Http404(f"Unknown example: {example_id!r}")
    load_system_into_session(repository, raw_system_data, workspace=workspace)
    return redirect("model-builder")


# Local dev tooling: files the DEBUG-only ``load_local_file`` route may open. Everything else 404s,
# so even a local GET endpoint never turns into an arbitrary file read.
LOCAL_FILE_ROOTS = (settings.BASE_DIR / "ai_sandbox" / "runs",)


def load_local_file(request):
    """DEBUG-only GET deep link that opens an exported ``.e-f.json`` from the local disk.

    Registered only when ``settings.DEBUG`` is true (see ``e_footprint_interface/urls.py``), it is what
    the AI sandbox report links to ("Open in interface") so a generated model lands on the canvas without
    the manual *Open file* upload. Like the docs deep link it replaces the active model without
    confirmation. ``path`` must resolve under one of ``LOCAL_FILE_ROOTS``.
    """
    raw_path = request.GET.get("path", "")
    path = Path(raw_path).resolve() if raw_path else None
    if path is None or not path.is_file() or not any(path.is_relative_to(root) for root in LOCAL_FILE_ROOTS):
        raise Http404(f"Not a loadable local file: {raw_path!r}")
    with open(path) as file:
        raw_system_data = json.load(file)
    workspace = SessionWorkspaceRepository(request.session)
    load_system_into_session(workspace.active_repository(), raw_system_data, workspace=workspace)
    return redirect("model-builder")
