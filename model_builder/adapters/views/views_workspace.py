"""Workspace endpoints for the two-model comparison builder.

Thin HTTP adapters over ``SessionWorkspaceRepository``:

  - ``switch-model`` flips the active slot server-side (so a refresh restores the selection) and
    rebinds the small shared chrome (system name, results buttons, edge toggle) via OOB swaps. The
    two canvases stay resident; the visible one is toggled client-side, so the switch costs no
    canvas re-render and preserves each canvas's transient UI state.
  - ``add-model`` adds the second model by duplication, blank/scratch, or file import; the new model
    becomes active. Every path goes through ``workspace.add_slot``, inheriting the distinct-system-id
    invariant and the shared-budget pre-check.
  - ``remove-model`` drops a slot, returning the workspace toward single-model mode.
  - ``compare`` renders the comparison dashboard, **re-built fresh on every visit** (no stale
    results): it shapes ``model_a.system.compare_to(model_b.system)`` through the thin
    ``ComparisonService`` adapter (the library is the domain truth).
"""
import json
from copy import deepcopy

from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from efootprint.utils.tools import time_it

from model_builder.adapters.repositories import (
    InMemorySystemRepository, SessionWorkspaceRepository, SessionSystemRepository)
from model_builder.adapters.views.exception_handling import render_exception_modal_if_error
from model_builder.adapters.views.views import render_model_builder, build_workspace_slots
from model_builder.adapters.repositories.workspace_base import (
    MAX_SLOTS, system_id_of, with_fresh_system_id)
from e_footprint_interface.json_payload_utils import compute_json_size
from model_builder.domain.exceptions import PayloadSizeLimitExceeded
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.services import (
    ComparisonService, SystemImportService, SCRATCH_ID, get_example_system_data)


def _rendered_shared_chrome_oob(model_web) -> str:
    """OOB fragments that rebind the active-model chrome after a switch (no canvas re-render)."""
    from model_builder.adapters.presenters.oob_regions import _render_results_buttons, _render_edge_modeling_toggle

    system_name = (
        f"<p id='system-name' class='m-0 pe-3 text-truncate' "
        f"hx-swap-oob='outerHTML:#system-name'>{model_web.system.name}</p>")
    return system_name + _render_results_buttons(model_web, {}) + _render_edge_modeling_toggle(model_web, {})


def _rendered_active_model_role_oob(workspace, active_slot) -> str:
    """OOB rebind of the mobile active-model switcher (role pill → switch dropdown) after a slot switch.

    Regenerates the whole dropdown so its label and its "switch to the other model" target both track the
    now-active slot. Empty for single-model sessions — there is no switcher to retarget.
    """
    slots = workspace.list_slots()
    if len(slots) < 2:
        return ""
    return render_to_string(
        "model_builder/components/active_model_role.html",
        {"workspace_slots": [{"slot": s, "is_active": s == active_slot} for s in slots],
         "active_slot": active_slot, "oob": True})


@require_POST
@time_it
def switch_model(request):
    """Flip the active slot and rebind the shared chrome; the canvas toggle is client-side.

    The small shared chrome (#system-name, the results buttons, the edge toggle) is OOB-rebound for the
    now-active model, and the ``switchModelCanvas`` trigger drives the client-side canvas reveal. Every
    switch lands on the resident builder (the Compare view is dismissed client-side first, revealing the
    builder), so the chrome targets are always present.
    """
    workspace = SessionWorkspaceRepository(request.session)
    slot = int(request.POST["slot"])
    if slot not in workspace.list_slots():
        return HttpResponse(status=400)
    workspace.set_active_slot(slot)

    response = HttpResponse(
        _rendered_shared_chrome_oob(ModelWeb(workspace.repository_for(slot)))
        + _rendered_active_model_role_oob(workspace, slot))
    response["HX-Trigger"] = json.dumps({"switchModelCanvas": {"slot": slot}})
    return response


def open_add_model_import_panel(request):
    """Side panel for adding the second model from a file (distinct from the toolbar's "Open file")."""
    return render(request, "model_builder/side_panels/add_model_import.html", context={
        "header_name": "Add a model from a file", "save_button_label": "Add this model"})


def _restore_workspace(workspace, data: dict) -> None:
    """Prepare every model and its aggregate size before replacing any live slot."""
    models = data.get("models")
    if not isinstance(models, list) or not 1 <= len(models) <= MAX_SLOTS:
        raise ValueError(f"Workspace file must contain between 1 and {MAX_SLOTS} models.")
    import_service = SystemImportService(SessionSystemRepository.MAX_PAYLOAD_SIZE_MB)
    prepared = []
    system_ids = set()
    for model in models:
        incoming = import_service.import_system(SessionSystemRepository.upgrade_system_data(deepcopy(model)))
        if system_id_of(incoming) in system_ids:
            incoming = with_fresh_system_id(incoming)
        system_ids.add(system_id_of(incoming))
        prepared.append(incoming)
    size_mb = sum(compute_json_size(model).size_bytes for model in prepared) / (1024 * 1024)
    if size_mb > SessionSystemRepository.MAX_PAYLOAD_SIZE_MB:
        raise PayloadSizeLimitExceeded(size_mb, SessionSystemRepository.MAX_PAYLOAD_SIZE_MB)

    first_recovery = ModelWeb(InMemorySystemRepository(prepared[0])).to_json(save_computed_state=False)
    for key in ("interface_config", "efootprint_interface_version"):
        if key in prepared[0]:
            first_recovery[key] = deepcopy(prepared[0][key])

    for slot in workspace.list_slots():
        workspace.repository_for(slot).clear()
    workspace.repository_for(0).save_data(prepared[0], recovery_data=first_recovery)
    for slot in workspace.list_slots():
        if slot != 0:
            workspace.remove_slot(slot)
    for model in prepared[1:]:
        workspace.add_slot(model)

    slots = workspace.list_slots()
    requested = data.get("active_slot", 0)
    workspace.set_active_slot(slots[requested] if 0 <= requested < len(slots) else slots[0])


def _system_data_for_add(request, workspace):
    """Build the single-model document for the model the user asked to add.

    Three sources, all passed through the import service before ``add_slot`` saves them:
      - ``duplicate``: copy the complete active model (fresh System id, other object ids preserved)
        and propose the editable name ``"Copy of {name}"``;
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
        return get_example_system_data(SCRATCH_ID)

    system_data = workspace.active_repository().get_system_data()
    original_name = system_data["System"][system_id_of(system_data)]["name"]
    system_data = with_fresh_system_id(system_data)
    system_data["System"][system_id_of(system_data)]["name"] = f"Copy of {original_name}"
    return system_data


@render_exception_modal_if_error
@require_POST
def add_model(request):
    """Add a second model (duplicate / blank / import) and make it active."""
    workspace = SessionWorkspaceRepository(request.session)
    import_service = SystemImportService(SessionSystemRepository.MAX_PAYLOAD_SIZE_MB)
    raw_system_data = _system_data_for_add(request, workspace)
    with_calc = import_service.import_system(raw_system_data)
    new_slot = workspace.add_slot(with_calc)

    workspace.set_active_slot(new_slot)
    model_web = ModelWeb(workspace.repository_for(new_slot))
    if request.POST.get("source") == "import":
        request.session["simplified_inputs_opening_ids"] = [model_web.system.efootprint_id]
    return render_model_builder(request, model_web, show_example_picker=False, workspace=workspace)


@render_exception_modal_if_error
@require_POST
def remove_model(request):
    """Remove a slot and return to the surviving (now active) model."""
    workspace = SessionWorkspaceRepository(request.session)
    slot = int(request.POST["slot"])
    workspace.remove_slot(slot)

    model_web = ModelWeb(workspace.active_repository())
    return render_model_builder(request, model_web, show_example_picker=False, workspace=workspace)


@render_exception_modal_if_error
@time_it
def compare(request):
    """Render the comparison dashboard for the workspace's two models.

    A pure HX fragment swapped into the resident ``#comparison-view`` sibling — plain ``render`` (not
    ``htmx_render``): there is no full-page Compare route, so it must not fall through to the
    base.html branch on a non-HX request.

    Built fresh on every visit (no stale results): the two slots' models are wrapped, compared via the
    library's ``System.compare_to`` and shaped by the thin ``ComparisonService`` adapter. The dashboard
    is shown only when two models exist *and both are complete enough to compute* — the same readiness
    signal that gates the ⇄Compare tab. Otherwise (one model, or an incomplete second model) it returns
    an empty response rather than erroring (disabled-instead-of-error): the dashboard swaps into the
    resident ``#comparison-view`` sibling, so rendering a full builder there would nest a builder inside
    the comparison block. This path is defensive only — the ⇄Compare tab is already disabled in that
    state, so it is unreachable from the UI.
    """
    from model_builder.adapters.views.views import compare_enabled

    workspace = SessionWorkspaceRepository(request.session)
    workspace_slots = build_workspace_slots(workspace)
    if not compare_enabled(workspace_slots):
        return HttpResponse("")

    model_a, model_b = workspace_slots[0]["model_web"], workspace_slots[1]["model_web"]
    comparison = ComparisonService().build(model_a, model_b)

    # The comparison view is self-contained — no tab strip or per-model chrome of its own (those stay
    # resident in the hidden builder) — so it needs only the comparison view model and the chart payloads.
    # Plain render (not htmx_render): this is a pure HX fragment swapped into #comparison-view, never a
    # full-page route, so it must not go through htmx_render's non-HX → base.html branch.
    context = {
        "comparison": comparison,
        "paired_chart_json": json.dumps(comparison.paired_chart),
        "cumulative_chart_json": json.dumps(comparison.cumulative_chart),
        "decomposition_chart_json": json.dumps(comparison.decomposition_chart),
    }
    return render(request, "model_builder/compare/dashboard.html", context=context)
