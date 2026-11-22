"""Fresh-only AI bootstrap; generation details exist only in the returned response."""
from django.http import Http404
from django.views.decorators.http import require_POST
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.constants.units import u
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.utils.display import format_quantity_for_display

from model_builder.adapters.ai_provider import ProviderError, complete_mistral, is_available
from model_builder.adapters.repositories import SessionWorkspaceRepository
from model_builder.adapters.views.views import (
    load_system_into_session, prepare_system_for_session, render_model_builder)
from model_builder.application.ai_bootstrap.metrics import estimate_call
from model_builder.application.ai_bootstrap.service import generate
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.exceptions import ComputationMemoryLimitExceeded, PayloadSizeLimitExceeded
from model_builder.domain.services import SCRATCH_ID, SystemValidationService, get_example_system_data, is_empty_model
from model_builder.narrate import event, narrate


def _input_response(request, workspace, description, scope, error):
    # A failed preparation may have replaced request-local settings; recover only saved settings.
    model_web = ModelWeb(workspace.active_repository())
    narrate("A refusal brings **the panel back with the description and the scope posted**, under one message; "
            "the slot keeps the modeling it held, since nothing was saved.", lambda: {"scope": scope})
    return render_model_builder(request, model_web, show_example_picker=False, workspace=workspace, extra_context={
        "ai_panel": "input", "ai_prompt": description, "ai_scope": scope, "ai_error": error})


@require_POST
def start_ai_bootstrap(request):
    event("The user chooses to start a modeling with AI.")
    if not is_available():
        raise Http404
    workspace = SessionWorkspaceRepository(request.session)
    repository = workspace.active_repository()
    repository.interface_config = {}
    narrate("The active slot **restarts from an empty modeling**, loaded by `load_system_into_session` like any "
            "other, its interface settings dropped. The other slot keeps its own.", lambda: {"slot": repository.slot})
    model_web = load_system_into_session(repository, get_example_system_data(SCRATCH_ID), workspace=workspace)
    narrate("The builder comes back with **the description panel open and empty on Web only**, marked so that the "
            "browser's Edge modeling toggle, when on, selects Web + edge once, and no example picker.")
    return render_model_builder(request, model_web, show_example_picker=False, workspace=workspace, extra_context={
        "ai_panel": "input", "ai_prompt": "", "ai_scope": "web", "ai_scope_follows_edge_modeling": True})


def _impact_label(value):
    def quantity(kg):
        return f"{format_quantity_for_display(kg * u.kg):~}"

    if value is None:
        return None
    if hasattr(value, "min") and hasattr(value, "max"):
        return f"{quantity(value.min)} – {quantity(value.max)} CO2-eq"
    return f"{quantity(value)} CO2-eq"


@require_POST
def generate_ai_bootstrap(request):
    event("The user submits the description of their system.")
    if not is_available():
        raise Http404
    workspace = SessionWorkspaceRepository(request.session)
    repository = workspace.active_repository()
    description = request.POST.get("description", "").strip()
    scope = request.POST.get("scope")
    narrate("A generation **never overwrites work**: it goes on only while `is_empty_model` still reads the active "
            "slot's saved modeling as empty, and with a description to send and the scope it is asked in.",
            lambda: {"slot": repository.slot, "scope": scope, "description_characters": len(description)})
    if not is_empty_model(repository.get_system_data()):
        return _input_response(request, workspace, description, scope, "Start with AI again to replace this modeling.")
    if not description:
        return _input_response(request, workspace, description, scope,
                               "Describe your system before building your modeling.")
    try:
        generated, completion = generate(description, scope, complete_mistral)
    except ProviderError:
        return _input_response(request, workspace, description, scope,
                               "The AI provider could not complete the request. You can try again.")
    except (ValueError, TypeError, KeyError, ArithmeticError, AssertionError,
            InsufficientCapacityError, ComputationMemoryLimitExceeded):
        # Parsing, schema and library construction errors can contain generated text.
        return _input_response(request, workspace, description, scope,
                               "The AI answer could not be built into a modeling. "
                               "Review your description and try again.")

    try:
        raw = system_to_json(generated.system, save_computed_state=False)
        repository.interface_config = {}
        narrate("The graph is serialized without its computed state and **prepared as any imported modeling is**, by "
                "`prepare_system_for_session`: upgraded, recomputed, its id kept distinct from the other slot's.")
        prepared = prepare_system_for_session(repository, raw, workspace=workspace)
        narrate("`SystemValidationService` says whether the modeling **is complete enough to compute**. An incomplete "
                "one is refused, and nothing is saved.", lambda: {"system": prepared.system.name})
        valid = SystemValidationService().validate_for_computation(prepared).is_valid
    except PayloadSizeLimitExceeded:
        return _input_response(request, workspace, description, scope,
                               "The generated modeling exceeds this workspace's size limit. Try a smaller description.")
    except (ValueError, TypeError, KeyError, ArithmeticError, AssertionError,
            InsufficientCapacityError, ComputationMemoryLimitExceeded):
        return _input_response(request, workspace, description, scope,
                               "The generated modeling could not be computed. Review your description and try again.")
    if not valid:
        return _input_response(request, workspace, description, scope,
                               "The generated modeling is incomplete. "
                               "Describe its usages and infrastructure, then try again.")
    try:
        narrate("`ModelWeb` **saves the modeling once**, through the normal persistence boundary. Until this line the "
                "slot still held the empty one.")
        prepared.persist_to_cache()
    except PayloadSizeLimitExceeded:
        return _input_response(request, workspace, description, scope,
                               "The generated modeling exceeds this workspace's size limit. Try a smaller description.")
    except ComputationMemoryLimitExceeded:
        return _input_response(request, workspace, description, scope,
                               "The generated modeling could not be computed within this instance's memory limit.")

    # Estimation is optional and happens after publication; it cannot invalidate a saved graph.
    try:
        metrics = estimate_call(completion)
        impact = _impact_label(metrics["impact_kg"])
    except Exception:
        metrics, impact = {}, None
    narrate("The call's cost and impact are estimated by `estimate_call` **after the save**: an estimate that fails "
            "rejects nothing.", lambda: {"cost_usd": metrics.get("cost_usd"), "impact": impact})
    narrate("The response alone carries the description, the scope and the summary panel, whose checklist follows "
            "the scope: **nothing of the generation is stored**, in the session or in the saved modeling.",
            lambda: {"resolutions_shown": sum(item.how != "exact" for item in generated.resolutions),
                     "ignored_fields": generated.ignored_fields})
    return render_model_builder(request, prepared, show_example_picker=False, workspace=workspace, extra_context={
        "ai_panel": "summary", "ai_prompt": description, "ai_scope": scope, "ai_metrics": metrics, "ai_impact": impact,
        "ai_resolutions": [item for item in generated.resolutions if item.how != "exact"],
        "ai_ignored_fields": generated.ignored_fields,
    })
