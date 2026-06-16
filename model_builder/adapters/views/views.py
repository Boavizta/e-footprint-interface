import random
import string
from datetime import datetime
from io import BytesIO
from time import perf_counter
import json
import os
import gc

from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from efootprint import __version__ as efootprint_version
from efootprint.logger import logger
from efootprint.utils.calculus_graph import build_calculus_graph
from efootprint.utils.display import format_quantity_for_display, human_readable_unit
from efootprint.utils.tools import time_it
from e_footprint_interface import __version__ as interface_version

from model_builder.adapters.repositories import (
    SessionSystemRepository, SessionWorkspaceRepository, SessionCacheRepository)
from model_builder.adapters.label_resolver import LabelResolver
from model_builder.adapters.ui_config.canvas_help_info import build_canvas_class_help_info
from model_builder.adapters.views.source_table_row_editor_context import build_source_table_row_editor_context
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.entities.web_core.explainable_timeseries_utils import (
    get_web_explainable_from_attr,
    prepare_timeseries_chart_context,
    prepare_hourly_quantity_data,
    prepare_recurrent_quantity_data,
)
from model_builder.domain.entities.web_abstract_modeling_classes.explainable_objects_web import ExplainableObjectWeb
from model_builder.adapters.views.exception_handling import render_exception_modal_if_error, render_recovery_page
from model_builder.adapters.presenters.template_picker_presenter import build_picker_groups
from model_builder.adapters.ui_config.tour_steps import build_tour_steps
from model_builder.domain.services import (
    ProgressiveImportService, SCRATCH_ID, get_template_system_data, is_empty_model)
from utils import htmx_render, sanitize_filename, smart_truncate


def load_system_into_session(repository, raw_system_data, workspace=None):
    """Upgrade, recompute, wrap and persist a raw system dict into a workspace slot.

    Shared by reboot, template loading, and the empty-model initialization — the one place that
    turns a serialized System into the session-backed current model. ``repository`` targets a slot
    (the active slot by default). When ``workspace`` is given and holds a second model, the incoming
    system id is made distinct from the sibling slot first, so loading the same template/file into
    one slot while the other holds it never produces two slots with the same id (the web_id prefix
    invariant — see workspace_base).
    """
    system_data = SessionSystemRepository.upgrade_system_data(raw_system_data)
    import_service = ProgressiveImportService(SessionSystemRepository.MAX_PAYLOAD_SIZE_MB)
    system_data = import_service.import_system(system_data)
    if workspace is not None:
        system_data = workspace.distinctify_against_siblings(system_data, repository.slot)
    model_web = ModelWeb(repository, system_data)
    model_web.persist_to_cache()
    gc.collect()
    return model_web


def _requested_slot(request, workspace):
    """Resolve a ``slot`` request param to an occupied slot, defaulting to the active slot."""
    raw = request.GET.get("slot", request.POST.get("slot"))
    if raw is None:
        return workspace.active_slot()
    try:
        slot = int(raw)
    except (TypeError, ValueError):
        return workspace.active_slot()
    return slot if slot in workspace.list_slots() else workspace.active_slot()


def build_workspace_slots(workspace):
    """Build a render-ready list of the workspace's slots: one wrapped model per occupied slot.

    Each entry carries the slot index, its ``ModelWeb``, the system name, and whether it is active.
    The active slot's model is the shared chrome's ``model_web`` (toolbar, results panel, picker).
    """
    active_slot = workspace.active_slot()
    slots = []
    for slot in workspace.list_slots():
        model_web = ModelWeb(workspace.repository_for(slot))
        is_active = slot == active_slot
        slots.append({
            "slot": slot,
            "model_web": model_web,
            "name": model_web.system.name,
            "is_active": is_active,
            # Active canvas keeps the canonical structural ids; parked canvas suffixes them by slot so
            # nothing collides across the two resident canvases (see model_canvas_content.html).
            "suffix": "" if is_active else f"-{slot}",
        })
    return slots


def compare_enabled(workspace_slots) -> bool:
    """Whether the ⇄Compare tab may be enabled: two models, both complete enough to compute.

    Comparing reads each model's computed footprint, so an incomplete model (e.g. a freshly added blank
    one) cannot be compared — gate on the same results-readiness signal as the "Get results" button
    rather than on slot count, so the tab is disabled-instead-of-error (constitution §3.1, spec §4.2)
    instead of 500-ing when the comparison runs.
    """
    from model_builder.domain.services import SystemValidationService
    if len(workspace_slots) < 2:
        return False
    validator = SystemValidationService()
    return all(validator.validate_for_computation(slot["model_web"]).is_valid for slot in workspace_slots)


def render_model_builder(request, model_web, show_template_picker, workspace=None):
    """Render the builder canvas, optionally overlaying the first-run template picker.

    Renders the tab strip plus one resident canvas per workspace slot (active visible). When no
    ``workspace`` is given the caller already holds the active ``model_web`` only — a single-model
    render, the degenerate single-slot case. ``model_web`` is always the active slot's model: the
    shared chrome (toolbar, results panel, picker, tour) binds to it.
    """
    workspace_slots = build_workspace_slots(workspace) if workspace is not None else [
        {"slot": getattr(model_web.repository, "slot", 0), "model_web": model_web,
         "name": model_web.system.name, "is_active": True, "suffix": ""}]
    active_slot = next(s["slot"] for s in workspace_slots if s["is_active"])

    model_is_empty = is_empty_model(model_web.system_data)
    context = {"model_web": model_web, "class_help_info": build_canvas_class_help_info(),
               "show_template_picker": show_template_picker,
               "model_is_empty": model_is_empty,
               "workspace_slots": workspace_slots,
               "compare_enabled": compare_enabled(workspace_slots),
               "active_slot": active_slot,
               "tour_steps": build_tour_steps(is_blank=model_is_empty)}
    if show_template_picker:
        context["template_picker_groups"] = build_picker_groups()

    http_response = htmx_render(request, "model_builder/model_builder_main.html", context=context)

    if request.headers.get("HX-Request") == "true":
        # Lines updates are triggered at the after settle element, so might be triggered before initModelBuilderMain
        # and cause an error, unless we remove all lines before.
        http_response["HX-Trigger"] = "removeAllLines"
        http_response["HX-Trigger-After-Settle"] = "initModelBuilderMain"

    return http_response


@time_it
def model_builder_main(request):
    workspace = SessionWorkspaceRepository(request.session)
    repository = workspace.active_repository()
    try:
        model_web = ModelWeb(repository)
        if model_web.system_data is None:
            logger.info("No system data found in session, initializing with the empty 'scratch' baseline")
            model_web = load_system_into_session(repository, get_template_system_data(SCRATCH_ID))

        if efootprint_version != model_web.initial_system_data_efootprint_version:
            logger.info(f"Upgrading system data from version "
                        f"{model_web.initial_system_data_efootprint_version} to {efootprint_version}")
            model_web.persist_to_cache()
            logger.info("Upgrade successful")
    except Exception as e:
        # A corrupt or unsupported session model would otherwise 500 here and leave the user with no
        # way out (the reset button lives on this very page). Fall back to the recovery page instead.
        # RAISE_EXCEPTIONS=1 keeps the raw traceback for debugging — same convention as upload_json.
        if os.environ.get("RAISE_EXCEPTIONS"):
            raise
        logger.exception("Failed to load the model from the session; rendering the recovery page")
        return render_recovery_page(request, error=e)

    # An empty model (fresh session, reset, or a returning user who never built anything) is met with
    # the template picker overlaid on the canvas; once there is content, entry goes straight to the model.
    return render_model_builder(
        request, model_web, show_template_picker=is_empty_model(model_web.system_data), workspace=workspace)


def recover_model(request):
    """Always-reachable, read-only escape hatch from a dead state (GET, never deserializes the model).

    This replaces the old GET /model_builder/reboot: it offers the user a way out without ever
    touching the model that may be crashing the deserializer. The destructive reset stays POST-only.
    """
    return render_recovery_page(request)


def download_raw_json(request):
    """Download the raw session model dict as-is, without going through ModelWeb.

    download_json rebuilds the model (and would crash on a corrupt one); this serves the stored
    JSON verbatim so a user in a dead state can still save their work and attach it to a bug report.
    """
    workspace = SessionWorkspaceRepository(request.session)
    repository = workspace.repository_for(_requested_slot(request, workspace))
    raw_system_data = repository.get_system_data()
    if raw_system_data is None:
        raise Http404("No model data found in the current session.")
    json_data = json.dumps(raw_system_data, indent=4)
    current_date_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    response = HttpResponse(json_data, content_type="application/json")
    response["Content-Disposition"] = f"attachment; filename={current_date_time} UTC recovered-model.e-f.json"
    return response


@require_POST
def reset_model(request):
    """Discard the current model, reset to the empty 'scratch' baseline and re-open the picker.

    POST-only: it destroys the session model, so it must not be reachable by a bare GET
    navigation. The toolbar reset button confirms first when the model is non-empty.
    """
    workspace = SessionWorkspaceRepository(request.session)
    repository = workspace.active_repository()
    model_web = load_system_into_session(repository, get_template_system_data(SCRATCH_ID), workspace=workspace)
    if request.headers.get("HX-Request") != "true":
        # Non-HTMX callers (e.g. the recovery page's plain form) get a clean redirect to a fresh
        # GET of the builder, rather than the toolbar's in-place fragment swap.
        return redirect("model-builder")
    return render_model_builder(request, model_web, show_template_picker=True, workspace=workspace)


def open_import_json_panel(request):
    return render(request, "model_builder/side_panels/import_model.html", context={
              "header_name": "Import a model", "save_button_label": "Use your model"})


def download_json(request):
    workspace = SessionWorkspaceRepository(request.session)
    slot = _requested_slot(request, workspace)
    repository = workspace.repository_for(slot)
    model_web = ModelWeb(repository)
    system = model_web.system
    system_data_without_calculated_attributes = model_web.to_json(save_calculated_attributes=False)
    if repository.interface_config:
        system_data_without_calculated_attributes["interface_config"] = repository.interface_config
        system_data_without_calculated_attributes["efootprint_interface_version"] = interface_version
    json_data = json.dumps(system_data_without_calculated_attributes, indent=4)
    current_date_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    response = HttpResponse(json_data, content_type="application/json")
    filename = f"{current_date_time} UTC {system.name}"
    filename = sanitize_filename(filename)
    filename = smart_truncate(filename)
    response["Content-Disposition"] = f"attachment; filename={filename}.e-f.json"
    return response

@time_it
def upload_json(request):
    workspace = SessionWorkspaceRepository(request.session)
    repository = workspace.active_repository()
    import_error_message = ""
    data = None

    if "import-json-input" in request.FILES:
        file = request.FILES["import-json-input"]
        try:
            if file and file.name.lower().endswith(".json"):
                data = json.load(file)
                file.close()
            else:
                import_error_message = "Invalid file format ! Please use a JSON file\n"
        except ValueError:
            import_error_message = "Invalid JSON data\n"
        finally:
            if file:
                file.close()

        if data and not import_error_message:
            try:
                system_data = SessionSystemRepository.upgrade_system_data(data)
                import_service = ProgressiveImportService(SessionSystemRepository.MAX_PAYLOAD_SIZE_MB)
                system_data_with_calculated_attributes = import_service.import_system(system_data)
                # "Replace this model" writes into the active slot; distinctify so importing the same
                # file the sibling slot already holds doesn't produce two slots with one system id.
                system_data_with_calculated_attributes = workspace.distinctify_against_siblings(
                    system_data_with_calculated_attributes, repository.slot)
                model_web = ModelWeb(repository, system_data_with_calculated_attributes)
                if "interface_config" in data:
                    repository.interface_config = data["interface_config"]
                else:
                    repository.interface_config = repository.load_interface_config_from_session()
                model_web.persist_to_cache()
                return redirect("model-builder")
            except Exception as e:
                if os.environ.get("RAISE_EXCEPTIONS"):
                    raise e
                import_error_message += (
                    f"Not a valid e-footprint model ! Please use only input files generated by e-footprint "
                    f"or the interface. \nException raised: {type(e).__name__}: {e}")
            finally:
                gc.collect()

    context = {"import_error_modal_id": "error-import-modal", "import_error_message": import_error_message}
    model_web = ModelWeb(repository)
    if model_web.system_data:
        context["model_web"] = model_web
        context["class_help_info"] = build_canvas_class_help_info()
        workspace_slots = build_workspace_slots(workspace)
        context["workspace_slots"] = workspace_slots
        context["compare_enabled"] = compare_enabled(workspace_slots)
        context["active_slot"] = workspace.active_slot()

    http_response = render(request, "model_builder/model_builder_main.html", context=context)
    http_response["HX-Trigger"] = json.dumps({"resetLeaderLines": ""})
    http_response["HX-Trigger-After-Settle"] = json.dumps({"openModalDialog": {"modal_id": "error-import-modal"}})

    return http_response

@render_exception_modal_if_error
@time_it
def result_chart(request):
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    model_web.raise_incomplete_modeling_errors()

    http_response = htmx_render(
        request, "model_builder/result/result_panel.html", context={"model_web": model_web})
    http_response["HX-Trigger-After-Settle"] = "triggerResultRendering"

    return http_response


def get_calculus_graph(request, cache_key):
    cache_repository = SessionCacheRepository(request.session, namespace="calculus_graph")
    content_to_return = cache_repository.pop(cache_key)

    if content_to_return is None:
        return HttpResponse("Graph content expired.", content_type="text/plain", status=404)

    return HttpResponse(content_to_return, content_type="text/html")


@time_it
def display_calculus_graph(request, efootprint_id: str, attr_name: str, id_of_key_in_dict: str=None):
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    efootprint_object = model_web.get_web_object_from_efootprint_id(efootprint_id)
    iframe_height = 95
    cache_key = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    cache_repository = SessionCacheRepository(request.session, namespace="calculus_graph")

    web_attr = getattr(efootprint_object, attr_name)
    if id_of_key_in_dict is None:
        calculated_attribute = web_attr
    else:
        calculated_attribute = ExplainableObjectWeb(
            web_attr.efootprint_object[
                model_web.get_efootprint_object_from_efootprint_id(
                    id_of_key_in_dict,
                    "object_type unnecessary because the usage pattern necessarily already belongs to the system")],
            model_web)

    calculus_graph = build_calculus_graph(calculated_attribute)
    calculus_graph.cdn_resources = "remote"
    calculus_graph_html = calculus_graph.generate_html()
    size_start = perf_counter()
    size_bytes = len(calculus_graph_html.encode("utf-8"))
    size_result_mb = size_bytes / (1024 * 1024)
    size_computation_time_ms = (perf_counter() - size_start) * 1000
    logger.info(
        f"Calculus graph HTML size: {size_result_mb:.2f} MB "
        f"(computation took {size_computation_time_ms:.1f} ms)"
    )
    cache_repository.set(cache_key, calculus_graph_html, write_redis=False)

    url = reverse("get-graph", kwargs={"cache_key": cache_key})

    return render(request, "model_builder/calculus_graph.html", {
        "graph": {"url": url, "calculated_attribute": calculated_attribute}, "iframe_height": iframe_height
    })


@time_it
def download_sources(request):
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    sources = []

    for web_explainable_quantity_source in model_web.web_explainable_quantities_sources:
        display_value = format_quantity_for_display(web_explainable_quantity_source.value)
        source = web_explainable_quantity_source.source

        sources.append([
            LabelResolver.get_field_label(web_explainable_quantity_source.attr_name_web),
            web_explainable_quantity_source.modeling_obj_container.name,
            LabelResolver.get_class_label(web_explainable_quantity_source.modeling_obj_container.class_as_simple_str),
            display_value.magnitude,
            human_readable_unit(display_value.units),
            source.name if source else "",
            source.link if source else "",
            web_explainable_quantity_source.confidence or "",
            web_explainable_quantity_source.comment or "",
        ])

    wb = Workbook()
    ws = wb.active
    ws.title = "Sources"

    headers = [
        "Item name",
        "Attribute of",
        "Object type",
        "Value",
        "Unit",
        "Source name",
        "Source link",
        "confidence",
        "comment",
    ]
    ws.append(headers)

    for row in sources:
        ws.append(row)

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 30

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    system_name = model_web.system.name
    current_date_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    response = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f"attachment; filename={current_date_time}_UTC {system_name}_sources.xlsx"

    return response


@time_it
def source_table(request):
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    return render(request, "model_builder/result/source_table.html", {"model_web": model_web})


@time_it
def source_table_row_editor(request, object_id: str, attr_name: str):
    context = build_source_table_row_editor_context(
        SessionWorkspaceRepository(request.session).active_repository(), object_id, attr_name)
    return render(request, "model_builder/result/source_table_row_editor.html", context)


@time_it
def get_explainable_hourly_quantity_chart_and_explanation(
    request, efootprint_id: str, attr_name: str, id_of_key_in_dict: str=None):
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    context, _ = prepare_timeseries_chart_context(
        model_web, efootprint_id, attr_name, prepare_hourly_quantity_data, id_of_key_in_dict)

    # Rename for template compatibility
    context["web_ehq"] = context.pop("web_explainable")

    return render(
        request,
        "model_builder/side_panels/edit/calculated_attributes/calculated_attribute_chart.html", context=context)


@time_it
def get_explainable_recurrent_quantity_chart_and_explanation(
    request, efootprint_id: str, attr_name: str):
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    context, _ = prepare_timeseries_chart_context(
        model_web, efootprint_id, attr_name, prepare_recurrent_quantity_data)

    # Rename for template compatibility
    context["web_erq"] = context.pop("web_explainable")

    return render(
        request,
        "model_builder/side_panels/edit/calculated_attributes/recurrent_attribute_chart.html", context=context)


@time_it
def get_eco_logits_calculated_attribute_explanation(request, efootprint_id, attr_name):
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    explained_obj = getattr(model_web.get_web_object_from_efootprint_id(efootprint_id), attr_name)


    return render(
        request,
        "model_builder/side_panels/edit/calculated_attributes/eco_logits_calculated_attribute_explanation.html",
        {"explained_obj": explained_obj}
    )


@time_it
def get_calculated_attribute_explanation(request, efootprint_id, attr_name, id_of_key_in_dict=None):
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    explained_obj = get_web_explainable_from_attr(model_web, efootprint_id, attr_name, id_of_key_in_dict)
    literal_formula, ancestors_mapped_to_symbols_list = (
        explained_obj.compute_literal_formula_and_ancestors_mapped_to_symbols_list())

    return render(
        request,
        "model_builder/side_panels/edit/calculated_attributes/calculated_attribute_explanation.html",
        {
            "literal_formula": literal_formula,
            "ancestors_mapped_to_symbols_list": ancestors_mapped_to_symbols_list,
            "explained_obj": explained_obj
        }
    )
