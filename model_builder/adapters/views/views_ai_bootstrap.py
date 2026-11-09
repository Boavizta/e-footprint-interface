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


def _input_response(request, workspace, description="", error=""):
    # A failed preparation may have replaced request-local settings; recover only saved settings.
    model_web = ModelWeb(workspace.active_repository())
    return render_model_builder(request, model_web, show_example_picker=False, workspace=workspace,
                                extra_context={"ai_panel": "input", "ai_prompt": description, "ai_error": error})


@require_POST
def start_ai_bootstrap(request):
    if not is_available():
        raise Http404
    workspace = SessionWorkspaceRepository(request.session)
    repository = workspace.active_repository()
    repository.interface_config = {}
    model_web = load_system_into_session(repository, get_example_system_data(SCRATCH_ID), workspace=workspace)
    return render_model_builder(request, model_web, show_example_picker=False, workspace=workspace,
                                extra_context={"ai_panel": "input", "ai_prompt": ""})


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
    if not is_available():
        raise Http404
    workspace = SessionWorkspaceRepository(request.session)
    repository = workspace.active_repository()
    description = request.POST.get("description", "").strip()
    if not is_empty_model(repository.get_system_data()):
        return _input_response(request, workspace, description, "Start with AI again to replace this modeling.")
    if not description:
        return _input_response(request, workspace, description, "Describe your system before building your modeling.")
    try:
        generated, completion = generate(description, complete_mistral)
    except ProviderError:
        return _input_response(request, workspace, description,
                               "The AI provider could not complete the request. You can try again.")
    except (ValueError, TypeError, KeyError, ArithmeticError, AssertionError,
            InsufficientCapacityError, ComputationMemoryLimitExceeded):
        # Parsing, schema and library construction errors can contain generated text.
        return _input_response(request, workspace, description,
                               "The AI answer could not be built into a modeling. "
                               "Review your description and try again.")

    try:
        raw = system_to_json(generated.system, save_computed_state=False)
        repository.interface_config = {}
        prepared = prepare_system_for_session(repository, raw, workspace=workspace)
        valid = SystemValidationService().validate_for_computation(prepared).is_valid
    except PayloadSizeLimitExceeded:
        return _input_response(request, workspace, description,
                               "The generated modeling exceeds this workspace's size limit. Try a smaller description.")
    except (ValueError, TypeError, KeyError, ArithmeticError, AssertionError,
            InsufficientCapacityError, ComputationMemoryLimitExceeded):
        return _input_response(request, workspace, description,
                               "The generated modeling could not be computed. Review your description and try again.")
    if not valid:
        return _input_response(request, workspace, description,
                               "The generated modeling is incomplete. "
                               "Describe its usages and infrastructure, then try again.")
    try:
        prepared.persist_to_cache()
    except PayloadSizeLimitExceeded:
        return _input_response(request, workspace, description,
                               "The generated modeling exceeds this workspace's size limit. Try a smaller description.")
    except ComputationMemoryLimitExceeded:
        return _input_response(request, workspace, description,
                               "The generated modeling could not be computed within this instance's memory limit.")

    # Estimation is optional and happens after publication; it cannot invalidate a saved graph.
    try:
        metrics = estimate_call(completion)
        impact = _impact_label(metrics["impact_kg"])
    except Exception:
        metrics, impact = {}, None
    return render_model_builder(request, prepared, show_example_picker=False, workspace=workspace, extra_context={
        "ai_panel": "summary", "ai_prompt": description, "ai_metrics": metrics, "ai_impact": impact,
        "ai_resolutions": [item for item in generated.resolutions if item.how != "exact"],
        "ai_ignored_fields": generated.ignored_fields,
    })
