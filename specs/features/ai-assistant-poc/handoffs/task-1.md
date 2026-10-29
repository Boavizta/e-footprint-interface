# Task 1 — Generate path end to end
Repositories and implementation ranges: e-footprint-interface `e7ade421..9bb49296`.

## Review pointers
- `model_builder/urls.py` imports `views_ai_assistant` at URLconf load, so every deployment (flag off included) puts
  `ai_sandbox/` on `sys.path` and imports `dsl`, `providers`, `catalogs` at startup. Provider SDKs stay lazy inside
  `providers.py`; only the context processor import is deferred behind the flag.
- `call_metrics`: EcoLogits returns a scalar `gwp.value` for some catalog entries (Mistral-hosted models) and a
  `RangeValue` for others (Anthropic, OpenAI); both handled. `zai-glm-5-3-flash` snaps to `zai-glm-5-3`,
  `deepseek-v4-1-flash-1017` falls back to `mistral-small-latest`; the line names the catalog entry used.
- The non-empty branch raises "Editing is not available in this build." until task 3.

## Open concerns
- A POST on a session with no model (expired session) swallows `SessionExpiredError` into the feedback, then the
  re-render raises it again, so the app's generic expired-session handling applies; not reachable from the box,
  which only renders on a page with a model.
