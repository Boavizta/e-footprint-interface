"""Experimental AI assistant: builds the model from a free-text description, or edits it (dev app only).

On an empty model, runs the ai_sandbox stages in sequence (provider call, JSON parsing, DSL validation, system
build) and loads the result through the same persistence step as the example loader. On a non-empty model, sends
the model read back into the DSL with the request, applies the answer to the live model and persists once at the
end. Any failure is rendered in the assistant box with the model left untouched. The route is always registered;
the view 404s unless AI_ASSISTANT_ENABLED.
"""
import json
import sys

from django.conf import settings
from django.http import Http404
from django.views.decorators.http import require_POST
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.logger import logger

from model_builder.adapters.presenters.simplified_inputs import input_catalog
from model_builder.adapters.repositories import SessionWorkspaceRepository
from model_builder.adapters.views.views import load_system_into_session, render_model_builder
from model_builder.application.use_cases.simplified_inputs import persist_structural_change
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.services import is_empty_model

# The sandbox is a folder of scripts, not a package: import its modules by their top-level names, as its CLI does.
sys.path.insert(0, str(settings.BASE_DIR / "ai_sandbox"))
from catalogs import GENAI_PROVIDER_ALIASES, resolve_genai  # noqa: E402
from dsl import build_system, parse_json, validate_tolerating_extras  # noqa: E402
from edit import apply_edits, system_to_dsl  # noqa: E402
from providers import DEFAULT_MODELS, MODELS, complete  # noqa: E402

PROMPTS = settings.BASE_DIR / "ai_sandbox" / "prompts"
SYSTEM_PROMPT = (PROMPTS / "system_prompt.md").read_text()
EDIT_PROMPT = SYSTEM_PROMPT + "\n\n" + (PROMPTS / "edit_prompt.md").read_text()


class AssistantError(Exception):
    """A refusal or a failed stage; its message is shown as is."""


def call_metrics(model, completion):
    """Latency, token counts, USD cost and the call's own footprint estimated by EcoLogits."""
    metrics = {"latency_s": completion.latency_s, "input_tokens": completion.input_tokens,
               "output_tokens": completion.output_tokens, "cost_usd": completion.cost_usd(model)}
    try:
        from ecologits.tracers.utils import llm_impacts
        provider = GENAI_PROVIDER_ALIASES[MODELS[model][0]]
        catalog_name = resolve_genai(provider, model, [])[1]
        gwp_kg = llm_impacts(provider, catalog_name, completion.output_tokens, completion.latency_s).gwp.value
        if hasattr(gwp_kg, "min"):  # a RangeValue when the model's parameter count is only known as a range
            gwp_kg = (gwp_kg.min + gwp_kg.max) / 2
        metrics["footprint"] = f"{gwp_kg * 1e6:.0f} mg CO2-eq (EcoLogits, {catalog_name})"
    except Exception as error:
        metrics["footprint"] = f"footprint unavailable: {error}"
    return metrics


@require_POST
def ai_assistant(request):
    if not settings.AI_ASSISTANT_ENABLED:
        raise Http404
    model = request.POST.get("model")
    if model not in DEFAULT_MODELS:
        raise Http404(f"Unknown assistant model: {model!r}")
    workspace = SessionWorkspaceRepository(request.session)
    repository = workspace.active_repository()
    model_web = ModelWeb(repository)
    request.session["ai_assistant_model"] = model
    prompt = request.POST.get("prompt", "").strip()
    feedback, completion = {"model": model}, None
    try:
        if model_web.has_edge_objects:
            raise AssistantError("This model contains edge objects, which the assistant does not handle yet.")
        editing = not is_empty_model(model_web.system_data)
        if editing:
            current = json.dumps(system_to_dsl(model_web), indent=1)
            completion = complete(model, EDIT_PROMPT, f"Current model:\n{current}\n\nRequest: {prompt}")
        else:
            completion = complete(model, SYSTEM_PROMPT, prompt)
        data, _, error = parse_json(completion.text)
        if data is None:
            raise AssistantError(f"The answer is not JSON: {error}")
        if editing:
            feedback["applied"] = apply_edits(data, model_web)  # mutates the hydrated model, raises on the first problem
            persist_structural_change(model_web, input_catalog)  # the only write; prunes deleted simplified inputs
            feedback["note"] = data.get("note", "")
        else:
            spec, _ = validate_tolerating_extras(data)
            system, _ = build_system(spec)
            model_web = load_system_into_session(
                repository, system_to_json(system, save_computed_state=False), workspace=workspace)
            feedback["note"] = ("Values set from the description carry a comment; values the description "
                                "does not state use library defaults.")
    except Exception as error:  # provider error, invalid JSON, schema, build, refusal: all shown as is
        feedback["error"] = str(error) if isinstance(error, AssistantError) else f"{type(error).__name__}: {error}"
        model_web = ModelWeb(repository)  # the system was not written on this path
    if completion is not None:
        feedback.update(call_metrics(model, completion))
        feedback["raw"] = completion.text
        logger.info(
            f"AI assistant call: model={model} latency={completion.latency_s:.1f}s "
            f"input_tokens={completion.input_tokens} output_tokens={completion.output_tokens} "
            f"cost_usd={feedback['cost_usd']:.4f} prompt={prompt!r} answer={completion.text!r}")
    return render_model_builder(request, model_web, show_example_picker=False, workspace=workspace,
                                extra_context={"ai_feedback": feedback})
