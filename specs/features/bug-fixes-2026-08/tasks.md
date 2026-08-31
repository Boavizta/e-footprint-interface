# Bug fixes — August 2026

## Execution plan

**Deduplication verdict:** All four tasks have distinct causes: calculation-layer quantization, missing client-side blank-count handling, a closed-catalog widget mismatch, and Sankey restore/debounce boundary behavior.

### Feature-implement run 1

Execute Tasks **1 → 2 → 4 → 3**.

- Task 1 lands in `e-footprint`; Tasks 2, 4, and 3 land in `e-footprint-interface`.
- No task depends on another. Task 1 goes first because it corrects a silent public-API total; the two contained UI correctness fixes follow; the broader behavior-preserving form simplification lands last.
- Tasks 2 and 3 both touch client-side form behavior but not the same production files. Tasks 3 and 4 share E2E infrastructure only; keep their commits and regression scopes separate.
- After Task 1, validate the interface against the editable library worktree. No other cross-repository ordering or user validation gate remains.

## Task 1 — Preserve precision in `System.total_footprint`

**Status:** Done

**Goal:** Make the public hourly `total_footprint` conserve the same fabrication and energy streams as the category totals by removing calculation-layer rounding, without changing category membership or device allocation.

**Diagnostic:** [`diagnostics/genai-video-total-footprint-double-count.md`](diagnostics/genai-video-total-footprint-double-count.md)

**Repository:** `e-footprint`

**Files touched:**
- `e-footprint/efootprint/core/system.py` — return the full-precision total footprint timeseries.
- `e-footprint/CHANGELOG.md` — record the corrected API total under `Unreleased`.

**Tests added/changed:**
- `e-footprint/tests/test_system.py` — prove hourly and period-total conservation with fractional hourly inputs.
- `e-footprint/tests/api_utils_tests/test_minimal_serialization_contract.py` — verify the existing serialized-total round-trip and invalidation contract still passes.

**Acceptance:**
- On the unmodified GenAI video template, `system.total_footprint.sum()` equals the combined fabrication and energy category sums within normal floating-point tolerance (approximately 10.213 kg), and device fabrication remains included exactly once.
- `total_footprint` remains a labeled, explainable hourly kg timeseries with its existing serialized computed-slot contract.
- The interface category charts and Sankey remain unchanged and agree with the corrected API total at display precision.

**Depends on:** none

## Task 2 — Reject blank autosaving relationship counts in the client

**Status:** Done

**Goal:** Keep every autosaving relationship-count control consistent with persisted state by restoring its prior live numeric value and suppressing the HTMX request when a user commits a blank, while retaining backend validation and the existing semantics of zero and unlink.

**Diagnostic:** [`diagnostics/count-no-value-repeated-errors.md`](diagnostics/count-no-value-repeated-errors.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `e-footprint-interface/model_builder/templates/model_builder/object_cards/partials/dict_entry_count_unlink.html` — mark the shared count as required and expose the shared client hook.
- `e-footprint-interface/theme/static/scripts/model_builder_main.js` (or a focused count-control module) — capture the live value on focus, restore committed blanks, and suppress their requests before HTMX handles `change`.
- `e-footprint-interface/CHANGELOG.md` — record the user-visible validation fix under `Unreleased`.

**Tests added/changed:**
- `e-footprint-interface/js_tests/build_fixtures.py` and a focused inline-count Jest test — use the real partial to cover blank restoration/request suppression and valid zero/positive values.
- `e-footprint-interface/tests/e2e/objects/test_usage_journeys.py` and its page object — verify the object-card interaction without a modal or mutation.
- `e-footprint-interface/tests/unit_tests/adapters/views/test_views_dict_mutation.py` — keep blank/missing requests rejected without mutation as defense in depth.

**Acceptance:**
- Clearing and committing a shared autosaving count sends no update request, shows no exception modal, and immediately restores the value captured when editing began.
- Explicit zero, positive integers, and decimals retain their current save behavior; unlink remains the only removal action.
- Blank, missing, non-numeric, and negative direct requests remain rejected by the backend without mutation.

**Depends on:** none

## Task 3 — Replace closed catalog datalists with native selects

**Status:** Done

**Goal:** Render all four conditional closed-catalog fields as native single-choice `<select>` controls, preserving their provider/object-dependent option mappings and submitted values while removing incidental free-text entry and datalist-specific code.

**Diagnostic:** [`diagnostics/replace-datalists-with-selects.md`](diagnostics/replace-datalists-with-selects.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `e-footprint-interface/model_builder/adapters/forms/form_field_generator.py` — emit the existing string-select widget for conditional values while retaining dependency payloads.
- `e-footprint-interface/theme/static/scripts/dynamic_forms.js` — populate conditional selects directly, restore defaults, and clear stale child choices.
- `e-footprint-interface/model_builder/templates/model_builder/side_panels/dynamic_form_fields/datalist.html` — remove the unused datalist widget.
- `e-footprint-interface/specs/architecture.md` — document conditional select behavior instead of the datalist convention.

**Tests added/changed:**
- `e-footprint-interface/js_tests/dynamic_forms.test.js` — cover default restoration, dependent option replacement, and stale-selection clearing.
- `e-footprint-interface/tests/unit_tests/adapters/forms/test_form_field_generator.py` and owning web-wrapper snapshots — expect conditional selects with unchanged mappings.
- `e-footprint-interface/tests/integration/test_ecologits_video.py` — retain real-object cross-object option mapping coverage.
- Affected EcoLogits video and Boavizta E2E workflows — choose native select options and verify cascades and metadata round-trip.

**Acceptance:**
- GenAI model, video model, Boavizta instance type, and video-job resolution render as required native `<select>` controls; no production `<datalist>` or `input[list]` remains.
- Direct and dotted dependency cascades preserve valid saved/default values, clear stale values after parent changes, and cannot submit arbitrary catalog-invalid text.
- Existing source, confidence, and comment metadata round-trip unchanged, with no parser, persistence, schema, or library change.

**Depends on:** none

## Task 4 — Preserve Sankey threshold zero and immediate-close changes

**Status:** Done

**Goal:** Keep the existing repository-owned Sankey settings persistence while ensuring a saved `0%` threshold renders as zero and a released threshold value is submitted before an immediate Results close detaches the form.

**Diagnostic:** [`diagnostics/sankey-aggregation-threshold-persistence.md`](diagnostics/sankey-aggregation-threshold-persistence.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `e-footprint-interface/model_builder/templates/model_builder/result/sankey_card.html` — distinguish absent settings from numeric zero and submit the threshold range's final `change` immediately while retaining debounced drag previews and other existing control behavior.

**Tests added/changed:**
- `e-footprint-interface/tests/unit_tests/adapters/views/test_sankey_views.py` — prove a saved `0.0` threshold renders as zero.
- `e-footprint-interface/tests/e2e/test_sankey.py` and its page object — change the threshold without waiting, close Results immediately, reopen, and verify the final zero value persisted.

**Acceptance:**
- Existing non-zero thresholds, and now `0%`, survive closing and reopening Results.
- Releasing a threshold and immediately closing Results preserves that final value on reopen; new cards still default to `1%`.
- Persistence remains in `repository.interface_config["sankey_diagrams"]`; no close-time endpoint, schema change, or library change is introduced.

**Depends on:** none
