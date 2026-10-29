# Task 2 — Builder tables and read-back
Written 2026-10-29 against e-footprint-interface `0899c3c4` (efootprint from PyPI in the venv).
Plan: [1.1 shared builders](../plan.html#shared) · [1.4 edit, "Reading the model back"](../plan.html#edit).
Task: [tasks.md](../tasks.md#task-2--builder-tables-and-read-back).
Status: under review

## Start here
- `build_system` — `ai_sandbox/dsl.py:229` — the one function to split; each section loop body becomes `build_server`, `build_genai_api`, `build_job`, `build_step`, `build_journey`, `build_usage_pattern` with the signatures in the plan's 1.1 snippet.
- `_opt` — `ai_sandbox/dsl.py:138` — the per-field call whose arguments become the `*_FIELDS` tables.
- `_Shared` — `ai_sandbox/dsl.py:174` — gains an optional seed of existing devices, networks and countries (dicts keyed by archetype, network kind and country key) so an edit reuses "Default smartphone" instead of adding a second one.
- `_volume_timeseries` — `ai_sandbox/dsl.py:144` — its `form_inputs` keys are the ones the read-back inverts: `initial_volume`, `initial_volume_timespan`, `net_growth_rate_in_percentage`.
- `ModelWeb.system` — `model_builder/domain/entities/web_core/model_web.py:112` — a web wrapper; `model_web.system.modeling_obj` is the library `System`, which exposes `servers`, `jobs`, `usage_journeys`, `usage_patterns` (verified on the built handwritten case).
- `InMemorySystemRepository(initial_data=...)` — `model_builder/adapters/repositories/in_memory_system_repository.py:18` — how `tests/integration/test_edge_modeling_toggle_oob.py:20` builds a `ModelWeb` without Django.

## Change along the code path
1. `dsl.py`: add `SERVER_FIELDS`, `STORAGE_FIELDS`, `JOB_FIELDS`, `STEP_FIELDS` exactly as the plan's 1.1 snippet, mapping DSL field → (library attribute, unit). Note `gpus` appears twice: on servers it maps to `compute`, on jobs to `compute_needed`; keep them in their own tables. A small `_apply_fields(kwargs, c, table)` replaces the repeated `_opt` calls.
2. Per-kind builders take name-to-object lookups (`servers`, `apis`, `jobs`, `journeys`) and the shared `_Shared`; `build_system` keeps its loops and dict accumulation, calling the builders. Cloud sizing and GenAI resolution stay as they are (`resolve_cloud_instance`, `resolve_genai`). The GPU/CPU job split stays keyed on `isinstance(server, GPUServer)`.
3. New `ai_sandbox/edit.py` with `system_to_dsl(model_web) -> dict` (plain JSON-ready dict, not a `ModelSpec`, so the view can `json.dumps` it). Walk the library objects, not the web wrappers:
   - servers from `system.servers`: `BoaviztaCloudServer` → `cloud_provider`/`instance_type` from `.provider.value`/`.instance_type.value`; `GPUServer` → `kind: "gpu"`, `gpus` from `compute`; a plain `Server` → name only. `storage_gb` from `server.storage.base_storage_need`, `carbon_intensity_g_per_kwh` from `average_carbon_intensity`. Values via `value.to(unit).magnitude` using the tables; the value's `comment` (when set) goes under `comments[field]`.
   - genai_apis from the `external_api` of jobs that have one (or `system.jobs` filtered on `EcoLogitsGenAIExternalAPI`): `provider` and `model_name` from `.value`.
   - jobs from `system.jobs`: `server` or `genai_api` by name, numeric fields by `JOB_FIELDS` (`output_tokens` only for GenAI jobs; `gpus` only for `GPUJob`, `cpu_cores` otherwise).
   - journeys from `system.usage_journeys`, steps from `uj_steps` (a `WeightedExplainableObjectDict`; keys are the steps in order) with `jobs` listed as many times as each weight (`st.jobs.items()` gives `(job, weight)` with `weight.value.magnitude`; the handwritten case's "Chef answer" has weight 2).
   - usage_patterns from `system.usage_patterns`: `journey` is the single key of `usage_journeys`; `device` from the device name ("Default smartphone" → `smartphone`, same for laptop, screen, box; empty list → `"none"`; any other name passed as is); `network` from the network name ("Default mobile network" → `mobile`, otherwise `wifi`); `country` from `country.name` upper-cased with spaces as underscores; `volume` and `growth_pct_per_year` from `hourly_occurrences.form_inputs` when it is an `ExplainableHourlyQuantitiesFromFormInputs` (`initial_volume`, `initial_volume_timespan`, `net_growth_rate_in_percentage`), otherwise the yearly total of the series with `per: "year"` and growth 0.
   - `system_name` from `system.name`.
   The read-back is lossy on purpose: anything the DSL cannot say is omitted.

Returned result: a dict that `validate_tolerating_extras` accepts and `build_system` rebuilds to the same footprint within 1 %.

## Earlier tasks
Task 1 moved `parse_json` and `validate_tolerating_extras` into `dsl.py`; import them from there in the test. Nothing else from task 1 is needed; this task is independent of Django.

## Reuse
- `Resolution` and the `resolutions` list stay the record of catalog choices; builders keep appending to it.
- `run.py --dry-run` is the regression check for the refactor; `evaluate()` in `run.py` calls `build_system` and must not change.
- Test fixture pattern: `system_to_json(system, save_computed_state=False)` → `InMemorySystemRepository(initial_data=...)` → `ModelWeb(repository)`.

## Invariants and traps
- Behavior-preserving refactor: the exported model of the dry run must be the same (total 17044.4 kg on the handwritten case before the change).
- Every CPU server is still a Boavizta cloud instance in the builder; the read-back must not turn a plain `Server` from an example into a cloud instance (it emits name only, and task 3 refuses sizing edits on it).
- Units: `u.GB_stored`, `u.kB_stored`, `u.MB_ram`, `u.cpu_core`, `u.gpu` are the library's typed units; convert with `.to(unit).magnitude` so a value stored in another unit still reads back as a plain number.
- Keep `dsl.py` importable without Django and without the interface package; `edit.py` imports `ModelWeb` only for the type, so a plain import of `model_builder` is acceptable there (the view runs inside Django).
- Sandbox stays a folder of top-level modules; `edit.py` imports `dsl` and `catalogs` by name like the others.

## Validation
- Row 6 in `tests/integration/test_ai_assistant.py`: handwritten case → `build_system` → export → `ModelWeb` → `system_to_dsl` → `validate_tolerating_extras` → `build_system`; compare `system.total_footprint.sum()` of both within 1 %. Also assert the round trip keeps the step weights (the "Ask a question" step lists "Chef answer" twice) and the comments on `Photo store.storage_gb` and `Recipe thumbnails.data_transferred_kb`.
- `poetry run python ai_sandbox/run.py --dry-run ai_sandbox/cases/_handwritten_01_recipe_app.json` prints the same `total_kg_co2e_over_horizon`.
- `poetry run pytest tests --ignore=tests/e2e`. The Boavizta API is called during the build (network), as the existing sandbox dry run already does.

## Out of scope
`apply_edits`, the edit prompt and the view branch (task 3); any change to the prompts or cases.

## Unverified
- Whether `usage_journeys` on a `UsagePattern` is always a single-entry dict in the models testers load; if an example has two journeys on one pattern, emit the first and let the rest stay untouched (lossy by design).
- Whether a non-form `hourly_occurrences` (an example loaded from JSON) exposes a yearly sum conveniently; `value.sum()` on the series is the fallback, settle it on `ecommerce`.
