# Task 1 — Generate path end to end
Written 2026-10-29 against e-footprint-interface `0899c3c4` (efootprint from PyPI in the venv, EcoLogits 0.11.3).
Plan: [1.2 the box](../plan.html#box) · [1.3 generate](../plan.html#generate) · [1.5 feedback](../plan.html#feedback).
Task: [tasks.md](../tasks.md#task-1--generate-path-end-to-end).
Status: under review

## Start here
- `load_example` — `model_builder/adapters/views/views_onboarding.py:35` — the view to copy: workspace, active repository, `load_system_into_session`, `render_model_builder(..., show_example_picker=False, workspace=workspace)`.
- `render_model_builder` — `model_builder/adapters/views/views.py:124` — builds the context dict at line 150; add `extra_context=None` and `context.update(extra_context or {})` before `htmx_render`. It already computes `model_is_empty` (line 148) and the template sees it.
- `is_empty_model` — `model_builder/domain/services/empty_model.py:19` — the app's emptiness rule, used for the copy switch and the branch.
- `edge_modeling_doc_url` — `model_builder/adapters/context_processors.py:5` — the only existing context processor; register the new one beside it in `e_footprint_interface/settings.py:93`.
- `#panel-result-btn` — `model_builder/templates/model_builder/model_builder_main.html:33` — the box is included right after this block, inside `#model-builder-page`; line 20 shows the page-wide `hx-disabled-elt="button:not(:disabled)"`.
- `ModelWeb.has_edge_objects` — `model_builder/domain/entities/web_core/model_web.py:368` — the template guard and the refusal check.
- `complete`, `MODELS`, `DEFAULT_MODELS`, `Completion.cost_usd` — `ai_sandbox/providers.py` — the provider adapter and price table; `MODELS[name][0]` is the provider key for the API-key presence check.
- `parse_json`, `validate_tolerating_extras` — `ai_sandbox/run.py:42` and `:56` — move both to `ai_sandbox/dsl.py` (they only need `json`, `re`, `pydantic.ValidationError` and `ModelSpec`); `run.py` imports them back from `dsl`.
- `resolve_genai`, `GENAI_PROVIDER_ALIASES` — `ai_sandbox/catalogs.py:86` and `:64` — the EcoLogits catalog lookup reused for the footprint line.

## Change along the code path
1. `ai_sandbox/providers.py`: `DEFAULT_MODELS = ["zai-glm-5-3-flash", "claude-haiku-5-5", "gpt-6-luna", "deepseek-v4-1-flash-1017", "zai-glm-5-3"]` (PLAN-UPDATE-03). Update the comment above it in one clause.
2. `settings.py`: `AI_ASSISTANT_ENABLED = env.bool("AI_ASSISTANT_ENABLED", default=False)` next to `EDGE_MODELING_DOC_URL` (line 193); add `"model_builder.adapters.context_processors.ai_assistant"` to the context processors list.
3. `context_processors.py`: `ai_assistant(request)` per the plan snippet in 1.2. When the flag is on it returns `AI_ASSISTANT_MODELS` as `[(name, available)]` over `DEFAULT_MODELS` and `AI_ASSISTANT_DEFAULT_MODEL`, the first available name (or the first name when none is available), so the template can preselect it when the session holds no choice. Import the sandbox names lazily from the view module so flag-off deployments never touch the sandbox.
4. `views_ai_assistant.py`: the plan's 1.3 view verbatim, without the `edit` import (task 3 adds it). The non-empty branch raises `AssistantError("Editing is not available in this build.")`. Insert the sandbox dir on `sys.path` once at module import, as `ai_sandbox/run.py:26` does, then import `dsl`, `providers` and `catalogs` by their top-level names. Read `SYSTEM_PROMPT` from `ai_sandbox/prompts/system_prompt.md` at import. Use `request.POST.get("model")` and 404 when it is not in `DEFAULT_MODELS`. Use `efootprint.logger.logger` for the one `logger.info` line (model, latency, input and output tokens, cost, then the prompt and the answer text).
5. `call_metrics(model, completion)` in the same module: `latency_s`, `cost_usd`, tokens, and the EcoLogits footprint: `provider = GENAI_PROVIDER_ALIASES[MODELS[model][0]]`, `catalog_name = resolve_genai(provider, model, [])[1]`, then `llm_impacts(provider, catalog_name, completion.output_tokens, completion.latency_s)` from `ecologits.tracers.utils` (signature verified: `(provider, model_name, output_token_count, request_latency, electricity_mix_zone=None)`). `gwp.value` is a `RangeValue` with `min`/`max` in kg: report the midpoint in mg. Wrap the EcoLogits call in its own try so a catalog miss shows "footprint unavailable: ..." in the line instead of failing the request.
6. `urls.py`: `path("ai-assistant/", views_ai_assistant.ai_assistant, name="ai-assistant")` next to `load-example`.
7. `components/ai_assistant.html`: the plan's 1.2 markup, with the feedback block of 1.5: metrics line, then error in red or the note (and `applied` list when present, task 3), then `<details><summary>Raw answer</summary><pre>` when `ai_feedback.raw` exists. The select preselects `request.session.ai_assistant_model` when set, else `AI_ASSISTANT_DEFAULT_MODEL`. Style block in the component, `body.edge-modeling-on #ai-assistant { display: none; }` (the class is toggled by `theme/static/scripts/edge_modeling_toggle.js:24`).
8. `model_builder_main.html`: `{% if AI_ASSISTANT_ENABLED and not model_web.has_edge_objects %}{% include 'model_builder/components/ai_assistant.html' %}{% endif %}` after the `#panel-result-btn` div.
9. `CHANGELOG.md` under `[Unreleased]`, new `### Added` subsection above `### Fixed`: "Experimental, dev-only AI assistant that builds or edits the model from a description, behind `AI_ASSISTANT_ENABLED`."

Visible result: box at the lower right; after a successful generate the whole builder re-renders into `#main-content-block` with the new model and the feedback; after a failure, unchanged model plus the error text.

## Earlier tasks
None. Task 3 later adds the `edit` import, `EDIT_PROMPT` and the non-empty branch to this view, and the `applied` list to the template.

## Reuse
- `load_system_into_session` (`views.py:46`) validates the generated payload by reimporting it; nothing else to check.
- `system_to_json(system, save_computed_state=False)` from `efootprint.api_utils.system_to_json` returns the dict when no path is given.
- `SessionWorkspaceRepository(request.session).active_repository()` and `ModelWeb(repository)` as in `views_onboarding.py`.
- `settings` fixture of pytest-django for the flag in tests; `tests/integration/conftest.py` already fixes static storage for rendered views.
- The handwritten case `ai_sandbox/cases/_handwritten_01_recipe_app.json` is the fake answer for the success test (its DSL builds and exports today, total 17044.4 kg).

## Invariants and traps
- Session write discipline: the generate path writes the session only through `load_system_into_session`; the failure path must not persist anything except the remembered model name. Test 3 compares the system payload before and after.
- `request.session["ai_assistant_model"]` is a plain string; the template reads it via the `request` context processor already enabled (`settings.py:90`).
- Do not call the sandbox's `load_dotenv` from Django; keys come from the process environment.
- Do not import `ai_sandbox/run.py` from the view (it reads the prompt and imports `report` at import time); that is why the two helpers move to `dsl.py`.
- The route stays registered when the flag is off; the view raises `Http404`. The include guard keeps the box out of the page.
- Constitution: nothing computed outside the library; HTMX-first, one target, no OOB regions; the failure is rendered, not raised.
- Keep `pyproject.toml` untouched: the SDKs stay in the dev group, `pydantic` and `ecologits` are already locked.

## Validation
- New `tests/integration/test_ai_assistant.py`, Django `client`, `settings.AI_ASSISTANT_ENABLED = True` in each flag-on test, `monkeypatch.setattr(views_ai_assistant, "complete", fake)` where `fake` returns a `providers.Completion` (text, tokens, `latency_s`).
  - Row 1: fresh session, fake returns the handwritten case text; after POST the session system name is "Recipe app", the response contains the model name and "USD", no `id="example-picker"`.
  - Row 3: fake returns prose; `SessionSystemRepository(client.session).get_system_data()` equal before and after; the error text is in the response.
  - Row 4: `client.post("/model_builder/load-example/iot_industrial/")` first; POST a prompt; refusal text rendered, fake never called, payload equal.
  - Row 5: default settings, POST answers 404; `GET /model_builder/` has no `id="ai-assistant"`.
- `poetry run pytest tests --ignore=tests/e2e` and `poetry run python ai_sandbox/run.py --dry-run ai_sandbox/cases/_handwritten_01_recipe_app.json` (total unchanged after the helper move).
- Manual: `AI_ASSISTANT_ENABLED=1 MISTRAL_API_KEY=... poetry run python manage.py runserver`, empty model, one real generate; tune the box's `bottom` offset against the results band.

## Out of scope
The builder refactor and read-back (task 2), the edit path (task 3), the README paragraph (task 3), dev-app configuration (gate).

## Unverified
- The exact `ImpactsOutput` attribute path for the footprint (`impacts.gwp.value.min/max` or a scalar when the catalog gives one); settle by calling `llm_impacts("mistralai", "mistral-small-latest", 100, 1.0)` in a shell and handling both shapes.
- Whether `resolve_genai` snaps the open-weight names (`zai-glm-5-3-flash`, `deepseek-v4-1-flash-1017`) to a Mistral catalog entry; it returns a fallback name either way, so the line always renders.
