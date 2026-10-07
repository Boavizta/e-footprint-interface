# Task 2 — Restore accepted Simplified fields on rejected saves
Written 2026-10-07 against e-footprint-interface `f005dee5`.
Plan: [inline edit](../plan.html#inline-edit), [other saves](../plan.html#other-saves). Task: [Task 2](../tasks.md#task-2--restore-accepted-simplified-fields-on-rejected-saves).
Status: approved — implementation pending.

## Start here

- `edit_simplified_input()` and `simplified_input_field()` — `model_builder/adapters/views/views_simplified_inputs.py` — failed POST and existing single-field GET.
- `present_edited_input()` / `build_workspace_context()` — `model_builder/adapters/presenters/simplified_inputs.py` — existing OOB field rendering and targeted context.
- `field.html`, `editor.html`, `timeseries_panel.html` — `model_builder/templates/model_builder/simplified_inputs/` — field swap and old Retry/Discard/status controls.
- `saveEdit()`, `completeFocusedEditForExport()`, `workspace-mutation:finished` — `theme/static/scripts/simplified_inputs.js` — autosave, export and panel settlement.

## Change along the code path

On any rejected edit, open a new `SessionWorkspaceRepository(request.session).active_repository()` and `ModelWeb` after the exception. Build context for exactly `FieldAddress(object_id, attribute)` and render `field.html` with `oob=True`; combine that fragment with Task 1's error modal. Do not reuse the request-local `model_web`: `ModelingUpdate` can reject before persistence, `persist_to_cache()` can fail after mutating it, and presentation can fail after persistence has succeeded. The fresh repository read is authoritative in all three timings. Leave quick totals and Results untouched on failure; the success path through `present_edited_input()` remains as is.

Remove `failedEdits`, `markEditFailed()`, retry/discard actions, `data-save-failed` styling and the timeseries failed-save status element. After OOB swap and mutation settlement, mark the new field `Not saved` without retaining a draft. Native `reportValidity()` still prevents a request; ensure it also cancels a pending focused export when validation fails. A failed timeseries Save closes and empties the side panel after its accepted field arrives, as success already does. Keep `savedEdits` for unchanged-input and provenance-key behavior, `pendingExport` for successful save-aware export, and Configure's explicit draft.

## Earlier tasks

Task 1 supplies non-2xx modal responses that HTMX processes OOB and a `workspace-mutation:finished` failure based on HTTP status. This task adds the accepted-field OOB fragment to that response; it does not create a new error protocol.

## Reuse

`build_workspace_context(..., addresses={address})` and `field.html` already render one selected field; `present_edited_input()` shows how to render it OOB. `SessionWorkspaceRepository.active_repository()` selects the active model. `initializeEdits()` runs at mutation completion, after replacement. The existing `test_views_simplified_inputs.py` has repository setup and failure fixtures; `js_tests/simplified_inputs.test.js` exercises export sequencing.

## Invariants and traps

The accepted field includes provenance, not only its numeric value. A failure after persistence must restore the newly persisted value. Do not re-render the full workspace or recompute totals on error. The old submitted form may be detached by the OOB swap: locate the new form by its stable `data-value-prefix` before setting `Not saved`. A validation failure before any HTMX request must not leave `pendingExport` set. Keep the modal's panel-preservation flags for Configure and bookmark drafts; close only a failed timeseries Save through its mutation completion.

## Validation

Extend `tests/unit_tests/adapters/views/test_views_simplified_inputs.py` with before-persistence, persistence-rejection and after-persistence presentation failures; compare field value and provenance to a fresh repository read and assert no erroneous totals/results OOB. Update `js_tests/simplified_inputs.test.js` for replacement-form status, invalid focused export and failed Save panel cleanup. Update the distinct affected journeys in `tests/e2e/{test_simplified_inputs,test_weekly_pattern_builder}.py`; avoid duplicating cases. Run focused pytest, `npm run jest -- --runInBand`, and the affected E2E tests against the local server; Task 3 owns the complete gate.

## Out of scope

Removing cross-workspace failed-draft guards and updating the original spec, architecture or changelog; Task 3 owns those. No library or persistence-contract change.

## Unverified

The precise test seam for forcing a failure after persistence should be selected during implementation from `present_edited_input()` or its rendering helpers; assert repository state first so the test proves the late-failure case.
