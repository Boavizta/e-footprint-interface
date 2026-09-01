# Weekly-pattern builder for recurrent quantities — Tasks

**Status:** Tasks — under review.
**Spec:** [`spec.html`](spec.html). **Plan:** [`plan.html`](plan.html).

## Task 1 — Add the library weekly-pattern builder

**Status:** Done.

**Repository:** `e-footprint`.

**Goal:** Add the library-owned `ExplainableRecurrentQuantitiesFromWeeklyPattern` with intrinsic validation, canonical
168-hour composition, authored-state persistence, and human-readable comparison support. Attribute-specific permission for
negative values remains outside the builder itself; the interface derives that policy from the owning modeling class in
Task 2.

**Files touched:**
- `../e-footprint/efootprint/builders/timeseries/explainable_recurrent_quantities_from_weekly_pattern.py` (new)
- `../e-footprint/efootprint/builders/timeseries/__init__.py`
- `../e-footprint/specs/architecture/layers-and-modeling.html`
- `../e-footprint/specs/architecture/persistence.html`
- `../e-footprint/specs/architecture/comparison-and-display.html`
- `../e-footprint/CHANGELOG.md`

**Tests added/changed:**
- `../e-footprint/tests/builders/timeseries/test_explainable_recurrent_quantities_from_weekly_pattern.py` (new)
- `../e-footprint/tests/test_system_comparison.py`

**Acceptance:**
- The builder accepts the approved `{unit, profiles}` schema and reports intrinsic validation failures with a normalized
  field path, stable code, and user-facing message.
- Validation covers profile count and names, finite numeric values, total single-owner day coverage, integer hour bounds,
  ordered non-overlapping ranges, and adjacency; unused profiles remain valid.
- Composition produces a Pint quantity containing exactly 168 `float32` values ordered Monday 00:00 through Sunday 23:00,
  with profile baselines outside ranges, in `O(P + R + 168)` time.
- Copying and JSON serialization preserve every authored profile—including unused profiles—plus label, source, confidence,
  and comment; deserialization selects the new matcher without changing existing constant-builder loading.
- `form_inputs_for_display` lets system comparison describe the authored weekly pattern rather than comparing opaque arrays.
- The focused tests, full pytest suite, and JSON round-trip quality gate pass.

**Depends on:** none.

---

## Task 2 — Ship the composite weekly-pattern editor and save flow

**Status:** Done.

**Repository:** `e-footprint-interface`.

**Goal:** Register editable timeseries builders explicitly and let recurrent fields switch between the existing constant
form and the weekly-pattern form, with lossless local switching, inline validation, normalized JSON submission, and
save/reopen behavior. This task deliberately leaves the existing hourly preview unchanged and does not yet enable the
weekly side preview.

**Files touched:**
- `model_builder/adapters/forms/timeseries_builder_registry.py` (new)
- `model_builder/adapters/forms/form_field_generator.py`
- `model_builder/adapters/forms/form_data_parser.py`
- `model_builder/adapters/views/views_addition.py`
- `model_builder/adapters/views/views_edition.py`
- `model_builder/templates/model_builder/side_panels/dynamic_form_fields/dynamic_form_field.html`
- `model_builder/templates/model_builder/side_panels/dynamic_form_fields/explainable_timeseries_builder.html` (new)
- `model_builder/templates/model_builder/side_panels/dynamic_form_fields/recurrent_quantities_from_weekly_pattern.html` (new)
- `model_builder/templates/model_builder/side_panels/dynamic_form_fields/recurrent_quantities_from_constant.html`
- `theme/static/scripts/weekly_pattern_builder.js` (new)
- `theme/templates/base.html`
- `specs/architecture.md`
- `specs/conventions.md` if the delegated dynamic-editor behavior establishes a reusable convention
- `CHANGELOG.md`

**Tests added/changed:**
- `tests/unit_tests/adapters/forms/test_form_field_generator.py`
- `tests/unit_tests/adapters/forms/test_form_data_parser.py`
- `tests/unit_tests/adapters/views/test_views_addition.py` (new)
- `tests/unit_tests/adapters/views/test_views_edition.py`
- `tests/unit_tests/domain/entities/class_structures/*.json` snapshots affected by recurrent composite fields
- `tests/fixtures/form_data_builders.py`
- `tests/integration/test_edge_objects.py`
- `js_tests/build_fixtures.py`
- `js_tests/weekly_pattern_builder.test.js` (new)
- `tests/e2e/test_weekly_pattern_builder.py` (new)

**Acceptance:**
- The registry owns builder identifiers, labels, template names, ordering, and defaults; none of that UI metadata enters
  `efootprint`.
- Existing objects select their stored builder; new objects select the attribute default's builder. A selector is rendered
  only when more than one builder is available, so hourly fields retain their existing appearance.
- The composite field owns label, unit, source, confidence, comment, and the owning modeling class's negative-value policy.
  Baselines and range values accept negatives only when that library-declared attribute policy permits them.
- The editor implements profile add/remove/name, single-owner day stealing, baseline editing, first-free-gap range creation,
  chronological placement, overlap prevention, and all approved bounds and default behaviors.
- Switching builders retains both unsaved drafts, disables every inactive named control, marks the containing form modified,
  and submits only the selected builder. Closing the panel discards both drafts through the existing confirmation flow.
- The weekly editor submits one hidden normalized JSON value. The parser decodes it to typed `form_inputs`, excludes the
  UI-only selector, and preserves top-level source/confidence/comment handling.
- Client-invalid data cannot submit. If authoritative validation nevertheless rejects a stale or tampered save, the same
  path/code/message error shape identifies the corresponding visible control and no model mutation is persisted.
- A valid pattern saves, reopens with all authored state intact, and survives interface download/upload; constant recurrent
  fields and single-builder hourly fields do not regress.
- Focused Python/Jest/Playwright tests and the interface quality gates pass; `pyproject.toml` and `poetry.lock` do not retain
  a local editable `efootprint` dependency in the committed result.

**Depends on:** Task 1 released or installed locally as the interface's temporary editable dependency.

---

## Task 3 — Add the server-authoritative weekly side preview

**Repository:** `e-footprint-interface`.

**Goal:** Add the non-persisting preview protocol, reusable raw-timeseries chart preparation, and generic Chart.js lifecycle,
then use them to show the generated canonical week beside the weekly editor.

**Files touched:**
- `model_builder/adapters/views/views_timeseries_preview.py` (new)
- `model_builder/adapters/views/views.py`
- `model_builder/urls.py`
- `model_builder/domain/entities/web_core/explainable_timeseries_utils.py`
- `model_builder/templates/model_builder/side_panels/dynamic_form_fields/explainable_timeseries_builder.html`
- `model_builder/templates/model_builder/side_panels/timeseries_preview.html` (new)
- `theme/static/scripts/timeseries_preview.js` (new)
- `theme/static/scripts/weekly_pattern_builder.js`
- `theme/templates/base.html`
- `specs/architecture.md`
- `CHANGELOG.md`

**Tests added/changed:**
- `tests/unit_tests/adapters/views/test_views_timeseries_preview.py` (new)
- `tests/unit_tests/domain/entities/web_core/test_explainable_timeseries_utils.py`
- `js_tests/build_fixtures.py`
- `js_tests/timeseries_preview.test.js` (new)
- `js_tests/weekly_pattern_builder.test.js`
- `tests/e2e/test_weekly_pattern_builder.py`

**Acceptance:**
- One thin POST endpoint accepts object/field identity, the allow-listed registry builder identifier, normalized unsaved
  inputs, and preview identity; it derives field constraints server-side and carries no mutation instruction.
- The endpoint constructs only a temporary library builder, never hydrates or persists the full model, and returns exactly
  168 recurrent points with Monday-through-Sunday labels for a valid weekly draft.
- Timeseries-to-chart-data helpers accept raw library timeseries. Existing saved-chart callers add `ModelWeb` wrapper,
  formula, and ancestor context separately and continue to render unchanged.
- The generic browser module owns only Chart.js creation, update, destruction, and response selection; it performs no weekly
  composition or other modeling calculation.
- Valid committed edits refresh the side preview. Obvious invalid states suppress requests; authoritative errors map to the
  correct visible controls, update preview status, and retain the last valid chart.
- Continuous edits are debounced, range bounds refresh on commit, discrete profile/day actions refresh immediately when
  valid, and only the newest request may update a preview instance.
- Preview tests prove numerical parity with the library builder, non-persistence, responsive placement, error retention,
  stale-response protection, and lifecycle survival across HTMX panel swaps.
- Focused Python/Jest/Playwright tests and the interface quality gates pass.

**Depends on:** Task 2.

---

## Task 4 — Migrate the hourly usage preview onto the shared server path

**Repository:** `e-footprint-interface`.

**Goal:** Reuse the preview protocol for hourly usage-journey starts, move projection and aggregation back to the server-side
library/presentation path, and remove the duplicate browser implementation without changing the hourly form controls.

**Files touched:**
- `model_builder/adapters/views/views_timeseries_preview.py`
- `model_builder/domain/entities/web_core/explainable_timeseries_utils.py`
- `model_builder/templates/model_builder/side_panels/dynamic_form_fields/hourly_quantities_from_growth.html`
- `model_builder/templates/model_builder/side_panels/timeseries_preview.html`
- `theme/static/scripts/timeseries_preview.js`
- `theme/static/scripts/usage_pattern_timeseries.js`
- `specs/architecture.md`
- `specs/conventions.md` if the shared preview lifecycle becomes a reusable convention
- `CHANGELOG.md`

**Tests added/changed:**
- `tests/unit_tests/adapters/views/test_views_timeseries_preview.py`
- `tests/unit_tests/domain/entities/web_core/test_explainable_timeseries_utils.py`
- `js_tests/build_fixtures.py`
- `js_tests/timeseries_preview.test.js`
- `js_tests/usage_pattern_timeseries.test.js`
- `tests/e2e/objects/test_usage_patterns.py`
- `tests/e2e/test_timeseries.py`

**Acceptance:**
- The unchanged hourly controls submit their fixed growth inputs to the common preview endpoint, which constructs
  `ExplainableHourlyQuantitiesFromFormInputs` and returns pre-aggregated monthly and yearly chart series.
- Returned series match the library-generated hourly values under the existing aggregation strategy; the full multi-year
  hourly array is never transferred to the browser.
- The existing granularity selector switches between server-prepared series without recalculation or another request.
- `usage_pattern_timeseries.js` retains only form-specific constraints that are not naturally owned elsewhere; it no longer
  computes growth, aggregates timeseries, or owns Chart.js lifecycle.
- Existing hourly visibility, duration limits, add/edit/reopen behavior, responsive layout, and chart lifecycle remain intact.
- Focused parity and regression tests replace deleted browser-projection tests, and all interface quality gates pass.

**Depends on:** Task 3.

---

## Ordering rationale

Task 1 lands the domain capability and persistence contract in the owning library before the interface consumes it. Task 2
then provides a complete save/reopen milestone for weekly authoring while preserving the existing hourly path. Task 3 adds
the reusable preview protocol and completes the weekly user experience without coupling that already-large editor review to
chart infrastructure. Task 4 is a separate behavioral migration: the working hourly preview moves to the proven shared path
and its duplicate browser calculations can then be removed safely. Each boundary leaves both repositories working, and no
task spans repositories or splits a new abstraction from its first consumer.
