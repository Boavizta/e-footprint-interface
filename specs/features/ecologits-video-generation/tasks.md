# EcoLogits video-generation integration — Tasks

**Status:** Tasks — under review.
**Spec:** [`spec.md`](spec.md). **Plan:** [`plan.md`](plan.md).

Library tasks land in `e-footprint` on the `ecologits-video` branch (per `PRIVATE_INTEGRATION.md`). Interface tasks land in `e-footprint-interface`. Each task is one PR / one commit.

---

## Task 1 — Library: DAG helper refactor + video-generation trio + tests + CHANGELOG

**Status:** Done (2026-05-27, e-footprint branch `ecologits-video`). Implementation surfaced two
plan-implicit library mechanism gaps that were extended in scope (user-approved before edit):
- `ModelingObject.check_belonging_to_authorized_values` now supports dotted `depends_on` paths
  (`"external_api.model_name"`), needed for the cross-object Job.resolution → API.model_name cascade.
- `ExplainableObject.to_json` / `from_json_dict` now round-trip boolean values, needed for
  `SourceObject(True/False)` (`with_audio`) JSON persistence (constitution §2.3).

Docs case fixtures (`docs_sources/doc_utils/docs_case.py`, `generate_object_reference.py`,
`mkdocs.yml` nav) and `tests/api_utils_tests/test_json_to_system.py` were also updated to keep
mkdocs strict-build clean and the generation-order test green.

**Repo:** `e-footprint` (branch `ecologits-video`).

**Goal:** Land the three new modeling classes (`EcoLogitsVideoGenExternalAPIServer`, `EcoLogitsVideoGenExternalAPI`, `EcoLogitsVideoGenExternalAPIJob`), the supporting DAG helper refactor, unit mapping, defaults source, registration, and the test layer. After this task, a user with the library installed can declaratively model a video-generation service end-to-end via Python; no UI yet.

The DAG helper refactor (rename `ecologits_dag_structure.py` → plural, extract `get_formula(dag, task_name)`) is folded into this task because its only motivation is the second DAG consumer landing in the same diff — extracting it standalone would be over-engineering, and the whole branch merges back to `dev` together post-Vivatech, so the cherry-pick rationale doesn't hold.

The Server/API/Job are kept in one task because they're tightly coupled (Job → API → Server) and splitting them would create review boundaries with no behavioural pause point — the system isn't useful until all three exist together.

**Files touched:**
- `efootprint/builders/external_apis/ecologits/ecologits_dag_structure.py` → rename to `ecologits_dag_structures.py`; extract `get_formula(dag, task_name)`; export both LLM and video `__dependencies`.
- `efootprint/builders/external_apis/ecologits/ecologits_external_api.py` — update imports / call sites to `get_formula(llm_dag, task_name)`.
- Any other in-repo importers of the old singular module (grep `ecologits_dag_structure`).
- `efootprint/builders/external_apis/ecologits/ecologits_video_external_api.py` (new) — three classes per plan §2.
- `efootprint/builders/external_apis/ecologits/ecologits_unit_mapping.py` — add video DAG keys (`server_accelerator_power`, `server_accelerator_energy`, `server_accelerator_count`, `video_width`, `video_height`, `video_frames_count`, `server_lifetime`, `non_audio_weight`, and the `n / m / m1 / m2 / n1 / n2 / g` regression coefficients).
- `efootprint/builders/external_apis/ecologits/sources.py` (or wherever `ecologits_source` lives) — add `ecologits_video_defaults_source`.
- `efootprint/all_classes_in_order.py` — append the three new classes to `ALL_EFOOTPRINT_CLASSES` (none in `CANONICAL_COMPUTATION_ORDER`, builders sit outside `core/`).
- `CHANGELOG.md` — entry under upcoming release.

**Tests added/changed:**
- `tests/builders/external_apis/ecologits/test_ecologits_dag_structures.py` (new or renamed from the old singular test) — assert `get_formula(dag, task_name)` returns a non-empty formula string for every task name *both* the LLM integration and the new video Job consume. Covers the helper for both DAGs.
- Existing LLM EcoLogits tests stay green after the rename / call-site rewiring.
- `tests/builders/external_apis/ecologits/test_ecologits_video_external_api.py` (new):
  - Per-class construction with defaults; `param_descriptions` cover every `__init__` param.
  - `update_impacts` cache invalidation triggered by each of `duration`, `resolution`, `with_audio`, `data_center_pue`, `datacenter_location` (and only those).
  - Extracted attributes (`generation_latency`, `request_energy`, `request_usage_gwp`, `request_embodied_gwp`) carry correct units.
  - `update_request_duration` points at `generation_latency`.
  - `update_data_transferred` constructs `bits_per_pixel`, `fps`, and the local `datacenter_wue` (read from the EcoLogits per-provider config) fresh inside the method (no module-level singletons leaking into the calculation graph).
- `tests/builders/external_apis/ecologits/test_ecologits_unit_mapping.py` — extend to assert every key the video DAG produces has a unit mapping (no `KeyError` on materialization).
- `tests/builders/external_apis/ecologits/test_ecologits_video_integration.py` (new) — small system: one Server + one API + one Job. Assertions are **structural only** (units, presence, non-negative, monotonicity in `duration`), no literal magnitudes (per spec §5). JSON round-trip preserves calculated attributes (constitution §2.3).
- `tests/builders/external_apis/ecologits/test_video_frames_anti_drift.py` (new) — load-bearing: `ecologits.estimations.video.duration_to_frames(d) == int(d * 24 + 1)` for several `d`. Test docstring explains it's *meant* to fail loudly on upstream re-fits — do not soften.
- mkdocs build still clean (the new classes' docstrings and `param_descriptions` are picked up automatically via `EfootprintDescriptionProvider`).

**Acceptance:**
- Module renamed; old singular path removed; no dangling imports anywhere in the repo.
- Full library pytest suite green against the privately-pinned `ecologits`.
- JSON round-trip of a model containing the new classes preserves all calculated attributes.
- `mkdocs build` clean; reference page lists the new classes.
- `CHANGELOG.md` updated.

**Depends on:** none.

---

## Task 2 — Interface: boolean `SourceObject` widget + 3-level conditional cascade

**Repo:** `e-footprint-interface`.

**Status:** Done.

**Goal:** Land the two generic form-layer extensions the video feature needs, with no video-specific wiring yet. These are reusable capabilities (any future boolean `SourceObject`, any future three-level cascade) that touch widely-used form code and deserve independent review.

After this task: the form generator and JS cascade can render and propagate a boolean `SourceObject` and a `provider → model → resolution` chain, but no class in the system uses them yet (infrastructure landed, unused).

**Files touched:**
- `model_builder/adapters/forms/form_field_generator.py`:
  - New boolean branch alongside `list_values` / `conditional_list_values` (currently falls through to `input_type: "str"` around line 328, rendering a text input where the user has to type "True"/"False").
  - No change needed for chained cascades: the existing `conditional_list_values` block at lines 311–326 already emits one `dynamic_lists` entry per conditional field, which composes into a chain. The missing piece is JS-side propagation (next bullet).
- `model_builder/templates/model_builder/side_panels/dynamic_form_fields/bool.html` (new) — checkbox/toggle template, wired from the new generator branch.
- `theme/static/scripts/dynamic_forms.js` — extend cascade listeners (lines 129–142 datalist, 147–160 select) to propagate change events through a chain: when a parent changes, fire downstream listeners whose `filter_by` points at any field whose options were just repopulated.

**Tests added/changed:**
- `tests/unit/model_builder/adapters/forms/test_form_field_generator.py` (new or extended):
  - Generator emits the boolean template path and correct context for a synthetic class with a `SourceObject(True)` param.
  - Generator emits chained `dynamic_lists` entries for a synthetic class with a three-level `conditional_list_values` chain (parent provider → child model → grandchild resolution).
- JS unit test under `npm run jest` (extend the existing `dynamic_forms` suite) — simulate a parent-field change and assert the grandchild listener fires after the child's options repopulate.

**Acceptance:**
- Full Python test suite green (`poetry run pytest tests --ignore=tests/e2e`).
- `npm run jest` green.
- No existing form rendering changes (existing `list_values` / single-hop `conditional_list_values` flows produce byte-identical HTML).
- `bs_main.css` not edited by hand (any styling needed for the toggle is added in SCSS source and recompiled per `CLAUDE.md`).

**Depends on:** none. Lands in parallel with Task 1 if desired.

---

## Task 3 — Interface: video-generation wiring + tests + CHANGELOG

**Status:** Done. Implementation touched four files beyond the planned list, all mechanically
required to register the new classes and meet the task's own acceptance criteria
(user-approved scope, surfaced here):
- `model_builder/adapters/ui_config/class_ui_config.json` — labels for `EcoLogitsVideoGenExternalAPI`
  ("Gen AI video external API") and `EcoLogitsVideoGenExternalAPIJob` ("Gen AI video Job"), so the
  catalog select and doc links don't show raw class names.
- `model_builder/adapters/ui_config/field_ui_config.json` — `duration`
  + `with_audio` label entries (required by `test_objects_attributes_have_correspondences`); video
  classes added to `provider`/`resolution` containers for accuracy. (The `datacenter_location` +
  `data_center_pue` advanced-parameter entries were later removed once those became inferred
  calculated attributes rather than user inputs.)
- `tests/unit_tests/adapters/ui_config/test_ui_config_consistency.py` — excluded the internal
  `EcoLogitsVideoGenExternalAPIServer` stub (mirrors the LLM server stub).
- `tests/unit_tests/adapters/ui_config/test_description_provider.py` + the two `class_structures`
  snapshots — updated to include the new concrete class (additive).

The library was pinned for local dev by `pip install -e` of the `ecologits-video` worktree and the
private `ecologits` clone directly into the venv, leaving `pyproject.toml`/`poetry.lock` untouched at
the PyPI `21.1.2` pin (constitution gate 4). Note: the committed code imports the video classes, which
only exist in the `ecologits-video` library branch — it will not import against published `efootprint
21.1.2` until the post-Vivatech library publish / pin bump described in the spec.

**Repo:** `e-footprint-interface`. Requires the library task landed and either pinned via `poetry add ../e-footprint --editable` (reverted before commit) or via the published `ecologits-video` branch — per workspace `CLAUDE.md`.

**Goal:** Surface the new library classes in the model-builder UI, exercise them through integration + E2E tests, and update the interface CHANGELOG. This is the user-visible delivery.

**Files touched:**
- `model_builder/domain/efootprint_to_web_mapping.py` — `"EcoLogitsVideoGenExternalAPI": ExternalAPIWeb`, `"EcoLogitsVideoGenExternalAPIJob": JobWeb`.
- `model_builder/domain/entities/web_builders/services/external_api_web.py` — add `EcoLogitsVideoGenExternalAPI` to `ExternalAPIWeb.available_classes`.
- `CHANGELOG.md` — entry under upcoming release.

**Tests added/changed:**
- `tests/integration/...` (new) — load a fixture system JSON containing the new classes through `ModelWeb`; assert round-trip preserves calculated attributes and hourly footprints render through the existing results pipeline (no special casing).
- `tests/e2e/...` (new) — single E2E flow: add the video API through the model-builder UI (provider → model → resolution cascade exercised; boolean `with_audio` toggle exercised; no advanced parameters surfaced, since DC assumptions are inferred), attach a job, save, assert a non-zero footprint in results charts.

**Acceptance:**
- `poetry run pytest tests --ignore=tests/e2e` green.
- `poetry run pytest tests/e2e -n 4` green (E2E suite passes with the new test).
- The new API appears in the External API catalog in the UI; the three-level cascade only allows valid provider/model/resolution combinations; the boolean `with_audio` renders as a toggle, not a text input.
- Saved model round-trips through the JSON persistence layer.
- `CHANGELOG.md` updated.

**Depends on:** Task 1 (library classes must exist) and Task 2 (form infra must exist for the cascade and boolean to render correctly in the E2E test).

---

## Task 4 — Interface: remove the unused Task 2 three-level cascade JS (surfaced by Task 3 review)

**Status:** Done. Mandatory first step confirmed no in-one-form three-level chain exists anywhere:
every `conditional_list_values` `depends_on` target (`server_type`, `provider`,
`external_api.model_name`) is either a `list_values` attr or a cross-object dotted path — none is
itself a conditional attr of the same class, so the chain-propagation logic had no consumer. Reverted
`dynamic_forms.js` to the pre-Task-2 single-hop listener (dropped `topologicallySortDynamicLists` and
the downstream `dispatchEvent`) and rewrote `js_tests/dynamic_forms.test.js` down to a single
single-hop test (the original two tests both exercised the now-removed chain; the trimmed test keeps
coverage of the still-shipping parent-select → child-datalist path used by provider → model_name).
The Task 2 review's hidden-input handling in
`checkCurrentValueVsDefaultValue` is kept — it serves the boolean widget, not the chain. Jest green
(93 tests); the Python generator still emits chained `dynamic_lists` entries (JS-only revert) so
`test_form_field_generator.py` keeps its three-level emission test, with its comment corrected to
stop attributing in-form chaining to `dynamic_forms.js`. No CHANGELOG entry: internal dead-code removal
on an unreleased branch, no user-facing delta. Note: this removes the logic Task 5 option 2 would
resurrect — coordinate before doing both.

**Repo:** `e-footprint-interface`.

**Why:** The Task 3 review (commit `4eb51407`) found that the three-level chained-propagation added to
`theme/static/scripts/dynamic_forms.js` in Task 2 has **no consumer**. The feature splits the cascade
across two forms — provider → model in the `ExternalAPIWeb` form, and model → resolution in the
`JobWeb` form keyed cross-object on `external_api.model_name`. No single form ever holds a three-level
chain, so the chain-propagation + `topologicallySortDynamicLists` logic never fires. Per constitution
§1.4 ("minimize JS"), unused cascade complexity is a smell to remove.

**Goal:** Revert `dynamic_forms.js` to the single-hop listener (drop the downstream `dispatchEvent`
propagation and `topologicallySortDynamicLists`), and remove the now-unused JS unit test added in
Task 2 for chained propagation.

**First step (mandatory):** grep the whole form-config space for any genuine in-one-form three-level
chain before deleting, so removal doesn't break an unrelated consumer. If one exists, this task is
void and Task 2's JS stays.

**Depends on:** none (independent cleanup against Task 2's deliverable).

---

## Task 5 — Interface: make the Job form offer only valid resolutions for the chosen video API

**Status:** Done. One plan assumption was wrong and corrected during implementation (user-approved):
the plan set `filter_by = "{class}_external_api"` assuming the `external_api` reference renders as its
own `<select>`. It does not — `JobWeb.attributes_to_skip_in_forms` skips `external_api`, and the API is
chosen through the parent-selection helper `service_or_external_api` (value = API efootprint id). So the
generic generator can't hardcode the filter id. Instead a `conditional_list_filter_overrides` class
attribute was added to `ModelingObjectWeb` (default `{}`) and set on `JobWeb` to
`{"external_api": "service_or_external_api"}`; the generator's dotted-`depends_on` branch reads it,
falling back to `{class}_{first_segment}` otherwise. Knock-on: the `JobWeb_creation_dynamic_data.json`
snapshot's resolution entry was regenerated, and its mock (`_MockModelingObjectWeb`) gained a
`model_name` field so the dotted path resolves. Behaviour note: now that the single-hop listener is
wired, selecting an API fires `change` and **clears** the resolution input (existing
`dynamic_forms.js:139` semantics) — there is no longer a pre-filled default; the user picks from the
valid options. The E2E was updated accordingly (asserts the datalist contents + repopulation on API
change rather than a default value), and a second API on a different model was added to exercise the
repopulation. `specs/architecture.md` documents the cross-object dotted-`depends_on` generator pattern.

Post-review follow-up (separate commit): hoisted the shared stringified-conditional map and collapsed
the dotted/non-dotted branches onto a single `dynamic_lists.append`; documented why the cross-object
`[]` fallback is safe (off-catalog values rejected at submit, so an empty list only signals a global
`str()`-keying bug); added a real-object integration test
(`test_ecologits_video.py::test_job_form_resolution_datalist_is_keyed_by_real_api_with_correct_resolutions`)
that asserts the resolution datalist is keyed by real API ids with the correct per-model resolutions —
the only test exercising the real `str(model_name)` ↔ library `conditional_list_values` key match
(unit/snapshot use pre-matched stubs); and gave the snapshot mock divergent models (sora-2-pro vs
seedance-1.0) so the snapshot itself proves per-object differentiation.

**Repo:** `e-footprint-interface`.

**Desired behavior:** In the Job create/edit form, the `resolution` datalist offers exactly the
resolutions valid for the `EcoLogitsVideoGenExternalAPI` selected in that same form, and repopulates
when a different API is selected.

**Why it doesn't work today (surfaced by the Task 3 review):** `resolution`'s `conditional_list_values`
declares `depends_on="external_api.model_name"` (`ecologits_video_external_api.py:160`). The generator
builds the datalist's `filter_by` as the dotted `EcoLogitsVideoGenExternalAPIJob_external_api.model_name`
(`form_field_generator.py:322`), which is not a DOM id, so the single-hop cascade in `dynamic_forms.js`
bails at the `!filterElem` guard (`dynamic_forms.js:73`) and the resolution datalist is never populated
— it keeps `datalist.html`'s `"select a provider"` placeholder. Validity is enforced only server-side
(Task 1's `check_belonging_to_authorized_values` dotted-path check, on submit).

**Approach — collapse the cross-object hop at form-generation time (no new JS):** Each
`EcoLogitsVideoGenExternalAPI` instance has a fixed `model_name`, so the two-hop semantic
(`external_api → model_name → resolution`) is equivalent to a single hop keyed by the API object
itself. In the generator's `conditional_list_values` branch (`form_field_generator.py:313–328`),
detect a dotted `depends_on` and, instead of emitting `filter_by = "{class}_external_api.model_name"`:
- set `filter_by = "{class}_external_api"` — the `select_object` already rendered for the `external_api`
  reference (web_id `{class}_{first_segment}`, a real `<select>`);
- build `list_value` keyed by **available API object id**: for each object returned by
  `model_web.get_efootprint_objects_from_efootprint_type(<external_api type>)`, resolve the remaining
  path (`.model_name`) on the object, look up the library's
  `conditional_list_values["resolution"]["conditional_list_values"][model_name]`, and stringify the
  resolution values (matching the existing `str(...)` keying at line 324).

The existing single-hop datalist listener (`dynamic_forms.js:129–142`) then does the rest: selecting an
API fires `change`, the resolution datalist repopulates from the API id, and the once-only initial fill
covers edit mode. This is a genuine single hop — it does **not** reintroduce the chain-propagation
logic removed in Task 4, so the earlier Task 4/Task 5 conflict is void.

**Files touched:**
- `model_builder/adapters/forms/form_field_generator.py` — dotted-`depends_on` handling in the
  `conditional_list_values` branch (resolve first segment to its select field's web_id; re-key
  `list_value` by available-object id via `model_web`).
- `CHANGELOG.md` — entry under upcoming release (resolution dropdown now filters by the chosen API).
- (Optional boy-scout) `datalist.html:19` — the hardcoded `"select a provider"` option is generic-wrong
  for non-provider datalists; can be made neutral/blank now that resolution populates on load. Not
  required for the behavior.

**Tests added/changed:**
- `tests/unit_tests/adapters/forms/test_form_field_generator.py` — new test: a synthetic Job-like class
  with a dotted `depends_on` conditional field, given a `model_web` exposing two API objects on
  different models, emits one `dynamic_lists` entry whose `filter_by` is the API select's web_id and
  whose `list_value` is keyed by the two object ids, each mapping to that object's model's child values.
- `tests/e2e/objects/test_video_external_api_objects.py` — extend the video E2E: in the Job form the
  resolution datalist exposes the chosen API's valid resolutions; selecting an API on a different model
  repopulates them; saving a valid combo persists and round-trips.

**Acceptance:**
- `poetry run pytest tests --ignore=tests/e2e` green; `poetry run pytest tests/e2e -n 4` green;
  `npm run jest` green.
- In the UI, the Job form's resolution field offers only the selected API's resolutions and updates on
  API change; no `"select a provider"` text appears in the resolution datalist.
- No new JS; `dynamic_forms.js` unchanged.
- `CHANGELOG.md` updated.

**Depends on:** Task 3 (video wiring landed). No conflict with Task 4 (single-hop approach; chain logic
stays removed).

**Docs:** new generator pattern (cross-object dotted `depends_on` → precomputed single-hop datalist) —
note it in `specs/architecture.md` (or `conventions.md`) per the documentation-upkeep rule.

---

## Ordering rationale

- **Task 1 bundles the library work.** The DAG helper rename + `get_formula` extraction is motivated by the second consumer (the video DAG) landing in the same diff — extracting it standalone would be over-engineering, and the whole branch merges back to `dev` together post-Vivatech, so a separate cherry-pickable refactor commit isn't load-bearing. Server/API/Job are aggregated because the Job depends on the API depends on the Server — there's no behavioural pause point where the system would be useful with only one or two of them. Unit mapping, sources entry, class registration, tests, and CHANGELOG all live in the same diff because each would leave the system half-wired (tests red, mkdocs broken, JSON round-trip incomplete) if shipped alone.
- **Task 2 can land in parallel with Task 1.** Form infrastructure is generic and independent of any library work. Kept separate from Task 3 because the boolean widget and three-level cascade are reusable capabilities touching widely-used form code — they deserve a focused review that isn't mixed with the video-specific wiring. This is a real "infrastructure landed but unused" pause point: tests are green, no call sites exercise it yet.
- **Task 3 last.** Needs both Task 1 (library classes) and Task 2 (form infra) in place. This is the user-visible delivery and is the natural end of the feature.

Task 1 (library) and Task 2 (interface form infra) can proceed in parallel; Task 3 is the join point.
