# Task 1 — Extract shared generation, provider and metrics

Written 2026-11-09 against e-footprint-interface `1b2ea43740f76b1edcf7f345ed922582d2142bc4`; library reference `afc60887fa05c34d18d5969a45276bb08d3dace0`.
Plan: [generation](../plan.html#generation-call), [provider](../plan.html#mistral-call), [metrics](../plan.html#metrics), [CLI](../plan.html#retire). Task: [1](../tasks.md#task-1--extract-shared-generation-provider-and-metrics).
Status: under review.

## Start here

- `ModelSpec`, `parse_json`, `validate_tolerating_extras`, `build_system` — [ai_sandbox/dsl.py](../../../../ai_sandbox/dsl.py): existing generation pipeline, sourced builders and 2026 horizon to update.
- `Resolution`, `resolve_genai`, `resolve_cloud_instance`, `load_instance_specs`, `refresh_instance_specs` — [ai_sandbox/catalogs.py](../../../../ai_sandbox/catalogs.py): move the resolver/snapshot; separate network refresh from production.
- `_mistral`, `Completion`, `complete` — [ai_sandbox/providers.py](../../../../ai_sandbox/providers.py): adapter source, development contract/pricing and dispatch.
- `evaluate`, `attempt`, `replay`, `structural_checks` — [ai_sandbox/run.py](../../../../ai_sandbox/run.py); `write_summary` — [ai_sandbox/report.py](../../../../ai_sandbox/report.py): consumers and report imports affected by package conversion.
- `ai_assistant`, `call_metrics` — [current view](../../../../model_builder/adapters/views/views_ai_assistant.py); imports in [edit.py](../../../../ai_sandbox/edit.py) and [PoC tests](../../../../tests/integration/test_ai_assistant.py): live dependencies during extraction.

## Change along the code path

Move schema/builders, resolver, sizing snapshot and generation prompt into `model_builder/application/ai_bootstrap/`, with ordinary relative imports. Add `service.py` with the plan's `Completion` and `GeneratedModel` contracts: `generate(description, complete)` loads the packaged prompt, calls the injected callable once, and delegates text to `build_answer(text)`. The latter parses, validates and builds, returning resolutions and ignored-field paths. It never saves or imports adapters/Django.

Validate uniqueness of declaration keys before dictionary construction (servers, APIs, jobs and journeys); preserve repeated relationship references such as the handwritten fixture's two `Chef answer` jobs in one step. Do not confuse references with duplicate declarations. Reuse `_lookup`, `_Comments`, `_Shared`, library constructors and the existing timeseries builder. Change the one-year generation horizon to 2027-01-01 and clarify per-journey volumes in the shared prompt.

Add `adapters/ai_provider.py` for one fixed Flash call and the shared flag-plus-key availability check. Match the approved SDK parameters; reject non-success/truncated output, omit thinking chunks, retain actual token totals/latency/stop reason and unknown cache counts. Return small content-free failures without chaining content into user-visible/logged text. Keep CLI imports usable outside a configured Django request; isolate availability/configuration access appropriately.

`metrics.py::estimate_call(completion)` uses the plan's dated cost factors (0.15/0.03/0.50 USD per million) and explicit unscaled parent estimate. Preserve absent usage as unavailable, unknown cache usage as unknown with full-input pricing, and scalar/range kg until presentation. Provider output includes reasoning: never add an inferred split. Metric errors/non-finite results cannot reject a built modeling.

Evaluation/replay call shared `build_answer` and prompt while keeping benchmark-only scoring, stage diagnostics, exports, explicit CLI retries and other providers. They may inspect the shared schema for scoring, but must not retain a second construction pipeline. Flash dispatch delegates to the production adapter; adapt development reports/cost handling to nullable usage/cache without relabeling unknowns as observed zero. Convert runner/report imports to package imports; retain a small refresh command importing the moved resolver's constants/path. Move Mistral to runtime dependencies without unrelated upgrades.

## Earlier tasks

None. Task 2 consumes the exact service/provider/metrics contracts in the plan. Do not introduce repository or HTTP concerns into them. Adjust still-live PoC view/edit/test imports in this task so moving files does not break startup or editing before replacement; update the PoC test's hardcoded horizon expectation. Remove those obsolete consumers in Tasks 2/4, without compatibility modules or a second DSL copy.

## Reuse

Use [the handwritten answer](../../../../ai_sandbox/cases/_handwritten_01_recipe_app.json), library `system_to_json(..., save_computed_state=False)` / `json_to_system`, `InMemorySystemRepository`, `ModelWeb`, and existing form-builder/EditObjectUseCase patterns for the ordinary-edit check. Existing `efootprint.utils.display` helpers own quantity presentation. Keep `Resolution.as_dict()` usable by evaluation.

## Invariants and traps

Production application imports cannot point outward or into sandbox tooling. Requests never refresh catalogs or write evaluation artifacts. SDK debug logging stays off. Dated Flash cost and explicit parent impact are separate from catalog resolution of GenAI APIs *inside* the generated system. The SDK currently exposes no typed cached-token count; do not invent one. Preserve tolerant-extra reporting and shared infrastructure rather than tightening the approved schema arbitrarily.

## Validation

Add `tests/unit_tests/application/test_ai_bootstrap_service.py`, `test_ai_bootstrap_metrics.py`, `tests/unit_tests/adapters/test_ai_provider.py`, and Django-free `tests/integration/test_ai_bootstrap.py`.

Assert one call and no retries; exact fixed request settings; text/chunk/missing-usage behavior; content-free provider errors and truncation rejection; invalid JSON/schema/duplicate declarations/references; ignored paths; comments/defaults/shared objects/editable horizon; compute/export/reload and one normal edit. Stub the estimator to check parent identity, scalar/range preservation, known/unknown cached pricing, missing/non-finite/error estimates and no double-counted reasoning.

```sh
poetry run pytest tests/unit_tests/application/test_ai_bootstrap_service.py tests/unit_tests/application/test_ai_bootstrap_metrics.py tests/unit_tests/adapters/test_ai_provider.py tests/integration/test_ai_bootstrap.py
poetry run pytest tests/integration/test_ai_assistant.py
poetry run python -m ai_sandbox.run --help
```

Run offline dry-run and replay against the handwritten answer with output confined to a temporary directory; exercise `evaluate`/`replay` directly with temporary paths if the CLI's existing dry-run path remains fixed. Verify reports still contain stage outcomes, counts, substitutions and exports. No live provider/network catalog refresh, credentials or benchmark run. Confirm lock changes only move the SDK group.

## Out of scope

HTTP replacement, UI entry, report persistence, async inference, edge bootstrap, model selection and removing still-live editing before replacement exists.

## Unverified

No design blocker. SDK/estimator behavior must be exercised with stubs during implementation; task preparation did not invoke inference or application tests. Runtime-only installation smoke belongs to Task 4.
