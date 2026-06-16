"""Workspace endpoints for the two-model comparison builder (model-comparison Tasks 3–4).

Thin HTTP adapters over ``SessionWorkspaceRepository``:

  - ``switch-model`` flips the active slot server-side (so a refresh restores the selection) and
    rebinds the small shared chrome (system name, results buttons, edge toggle) via OOB swaps. The
    two canvases stay resident; the visible one is toggled client-side, so the switch costs no
    canvas re-render and preserves each canvas's transient UI state.
  - ``add-model`` adds the second model by duplication, blank/scratch, or file import; the new model
    becomes active. Every path goes through ``workspace.add_slot``, inheriting the distinct-system-id
    invariant and the shared-budget pre-check (constitution / plan §2.1, §4).
  - ``remove-model`` drops a slot, returning the workspace toward single-model mode.
  - ``compare`` renders the §4.2 comparison dashboard, **re-built fresh on every visit** (no stale
    results): it shapes ``model_a.system.compare_to(model_b.system)`` through the thin
    ``ComparisonService`` adapter (constitution §1.3 — the library is the domain truth).
"""
import gc
import json
import os

from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.comparison.duplication import duplicate_system

from model_builder.adapters.repositories import SessionWorkspaceRepository, SessionSystemRepository
from model_builder.adapters.views.views import load_system_into_session, render_model_builder, build_workspace_slots
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.services import (
    ComparisonService, ProgressiveImportService, SCRATCH_ID, get_template_system_data)
from utils import htmx_render


def _rendered_shared_chrome_oob(model_web) -> str:
    """OOB fragments that rebind the active-model chrome after a switch (no canvas re-render)."""
    from model_builder.adapters.presenters.oob_regions import _render_results_buttons, _render_edge_modeling_toggle

    system_name = (
        f"<p id='system-name' class='m-0 pe-3 text-truncate' "
        f"hx-swap-oob='outerHTML:#system-name'>{model_web.system.name}</p>")
    return system_name + _render_results_buttons(model_web, {}) + _render_edge_modeling_toggle(model_web, {})


@require_POST
def switch_model(request):
    """Flip the active slot and rebind the shared chrome; the canvas toggle is client-side."""
    workspace = SessionWorkspaceRepository(request.session)
    slot = int(request.POST["slot"])
    if slot not in workspace.list_slots():
        return HttpResponse(status=400)
    workspace.set_active_slot(slot)

    model_web = ModelWeb(workspace.repository_for(slot))
    response = HttpResponse(_rendered_shared_chrome_oob(model_web))
    response["HX-Trigger"] = json.dumps({"switchModelCanvas": {"slot": slot}})
    return response


def open_add_model_import_panel(request):
    """Side panel for adding the second model from a file (distinct from the toolbar's "Open file")."""
    return render(request, "model_builder/side_panels/add_model_import.html", context={
        "header_name": "Add a model from a file", "save_button_label": "Add this model"})


def _restore_workspace(workspace, data: dict) -> None:
    """Restore both slots from a workspace envelope, then set the active pointer.

    The first model is loaded into slot 0 (replacing whatever is there); any remaining models are
    added through ``add_slot`` so the distinct-system-id guard and the shared budget both apply (and
    so a save that would blow the budget is rejected before the index changes). Existing extra slots
    are cleared first so re-importing always lands a clean two-slot workspace.
    """
    models = data.get("models") or []
    if not models:
        raise ValueError("Workspace file contains no models.")

    for slot in workspace.list_slots():
        if slot != 0:
            workspace.remove_slot(slot)

    # Each embedded model carries its own interface_config (Sankey settings etc.); restore it per slot
    # so the round-trip preserves it as the single-model upload does (plan §2.7). Slot 0: set it on the
    # repository before persist. Slot 1+: ProgressiveImportService already carries it into the with-calc
    # dict, which add_slot's save writes through (and with_fresh_system_id preserves it on a re-mint).
    slot_0_repository = workspace.repository_for(0)
    if "interface_config" in models[0]:
        slot_0_repository.interface_config = models[0]["interface_config"]
    load_system_into_session(slot_0_repository, models[0])
    for model in models[1:]:
        import_service = ProgressiveImportService(SessionSystemRepository.MAX_PAYLOAD_SIZE_MB)
        workspace.add_slot(import_service.import_system(SessionSystemRepository.upgrade_system_data(model)))

    slots = workspace.list_slots()
    requested = data.get("active_slot", 0)
    workspace.set_active_slot(slots[requested] if 0 <= requested < len(slots) else slots[0])


def _system_data_for_add(request, workspace):
    """Build the without-calc single-model document for the model the user asked to add.

    Three sources, all returning a recomputed (with-calc) document for ``add_slot`` to save:
      - ``duplicate``: deep-copy the active model via the library ``duplicate_system`` (fresh system
        id, object ids preserved) and propose the editable name ``"Copy of {name}"``;
      - ``blank``: the empty scratch baseline;
      - ``import``: an uploaded single-model file.
    """
    source = request.POST.get("source", "duplicate")

    if source == "import":
        file = request.FILES.get("import-json-input")
        if not file or not file.name.lower().endswith(".json"):
            raise ValueError("Invalid file format ! Please use a JSON file.")
        raw = json.load(file)
        file.close()
        return SessionSystemRepository.upgrade_system_data(raw)

    if source == "blank":
        return get_template_system_data(SCRATCH_ID)

    active_model = ModelWeb(workspace.active_repository())
    duplicated = duplicate_system(active_model.system.modeling_obj)
    system_data = system_to_json(duplicated, save_calculated_attributes=False)
    system_block = system_data["System"][duplicated.id]
    system_block["name"] = f"Copy of {active_model.system.name}"
    return system_data


@require_POST
def add_model(request):
    """Add a second model (duplicate / blank / import) and make it active."""
    workspace = SessionWorkspaceRepository(request.session)
    import_service = ProgressiveImportService(SessionSystemRepository.MAX_PAYLOAD_SIZE_MB)
    try:
        raw_system_data = _system_data_for_add(request, workspace)
        with_calc = import_service.import_system(raw_system_data)
        new_slot = workspace.add_slot(with_calc)
    except Exception as e:
        if os.environ.get("RAISE_EXCEPTIONS"):
            raise
        return _render_with_error(request, workspace, f"Could not add the model: {type(e).__name__}: {e}")
    finally:
        gc.collect()

    workspace.set_active_slot(new_slot)
    model_web = ModelWeb(workspace.repository_for(new_slot))
    return render_model_builder(request, model_web, show_template_picker=False, workspace=workspace)


@require_POST
def remove_model(request):
    """Remove a slot and return to the surviving (now active) model."""
    workspace = SessionWorkspaceRepository(request.session)
    slot = int(request.POST["slot"])
    try:
        workspace.remove_slot(slot)
    except ValueError as e:
        if os.environ.get("RAISE_EXCEPTIONS"):
            raise
        return _render_with_error(request, workspace, str(e))

    model_web = ModelWeb(workspace.active_repository())
    return render_model_builder(request, model_web, show_template_picker=False, workspace=workspace)


def _render_with_error(request, workspace, message):
    """Re-render the builder with an error modal (mirrors upload_json's failure path)."""
    from model_builder.adapters.ui_config.canvas_help_info import build_canvas_class_help_info
    from model_builder.adapters.views.views import compare_enabled

    model_web = ModelWeb(workspace.active_repository())
    workspace_slots = build_workspace_slots(workspace)
    context = {
        "model_web": model_web,
        "class_help_info": build_canvas_class_help_info(),
        "workspace_slots": workspace_slots,
        "compare_enabled": compare_enabled(workspace_slots),
        "active_slot": workspace.active_slot(),
        "import_error_modal_id": "error-import-modal",
        "import_error_message": message,
    }
    http_response = HttpResponse(render_to_string("model_builder/model_builder_main.html", context, request))
    http_response["HX-Trigger"] = json.dumps({"resetLeaderLines": ""})
    http_response["HX-Trigger-After-Settle"] = json.dumps({"openModalDialog": {"modal_id": "error-import-modal"}})
    return http_response


def compare(request):
    """Render the §4.2 comparison dashboard for the workspace's two models.

    Built fresh on every visit (no stale results): the two slots' models are wrapped, compared via the
    library's ``System.compare_to`` and shaped by the thin ``ComparisonService`` adapter. The dashboard
    is shown only when two models exist *and both are complete enough to compute* — the same readiness
    signal that gates the ⇄Compare tab. Otherwise (one model, or an incomplete second model) it falls
    back to the builder rather than erroring (disabled-instead-of-error, constitution §3.1): comparing
    an incomplete model would read a footprint that does not exist and 500.
    """
    from model_builder.adapters.views.views import compare_enabled

    workspace = SessionWorkspaceRepository(request.session)
    workspace_slots = build_workspace_slots(workspace)
    if not compare_enabled(workspace_slots):
        return render_model_builder(
            request, ModelWeb(workspace.active_repository()), show_template_picker=False, workspace=workspace)

    model_a, model_b = workspace_slots[0]["model_web"], workspace_slots[1]["model_web"]
    comparison = ComparisonService().build(model_a, model_b)

    context = {
        "comparison": comparison,
        "paired_chart_json": json.dumps(comparison.paired_chart),
        "cumulative_chart_json": json.dumps(comparison.cumulative_chart),
        "decomposition_chart_json": json.dumps(comparison.decomposition_chart),
        "workspace_slots": workspace_slots,
        "compare_enabled": True,
        "active_slot": workspace.active_slot(),
    }
    return htmx_render(request, "model_builder/compare/dashboard.html", context=context)
