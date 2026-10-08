# Task 6 — Guard workspace mutations

Updated 8 October 2026 to match the [consolidated review adjustments](../plan.html#save-errors); the original task boundary and baseline below are retained.

Written 2026-09-30 against e-footprint `96ea0d39` and e-footprint-interface `fe6c04e5`.
Plan: [one-at-a-time saves](../plan.html#saves). Task: [overview](../tasks.md#task-6). Status: approved.
Implementation: standard — extend current HTMX request hooks and per-XHR disabled-state snapshot to mutation controls and response settlement.

## Start here

- [`model_builder_main.js`](../../../../theme/static/scripts/model_builder_main.js): `htmx:beforeRequest`/`afterRequest` disabled-state snapshot and shared shell handlers.
- [`side_panel_utils.js`](../../../../theme/static/scripts/side_panel_utils.js): existing modified-panel warning; [`model_comparison.js`](../../../../theme/static/scripts/model_comparison.js): resident canvas, tab and Compare transitions.
- [`model_builder_main.test.js`](../../../../js_tests/model_builder_main.test.js): existing request-state tests; [`test_model_comparison.py`](../../../../tests/e2e/test_model_comparison.py): model switching while a panel is edited.

## Change along the code path

Extend the existing HTMX request lifecycle to guard workspace mutations across Modeling and Simplified inputs. Capture the initiating request's payload, lock editable controls, structural actions, view/model changes and export until its response updates settle, then restore controls while preserving genuinely disabled constraints. Suppress a second mutation rather than queueing it. Keep stateless timeseries previews, reading and scrolling available. Provide the small shared state/signals that later simplified-input JS uses for updating and failure statuses.

## Earlier tasks

None. Land before Tasks 7–10 so new autosave does not ship without request coordination. Task 9 adds Enter/blur deduplication for its own controls; do not build a generic queue here.

## Reuse

Build on the `WeakMap` snapshot for `hx-disabled-elt="button"` rather than replacing it. Preserve existing side-panel confirmation and Compare's same-model resident-panel behavior.

## Invariants and traps

Recognized validation modals return HTTP 422 and unexpected errors return HTTP 500. Use HTTP success for save settlement; `openModalDialog` only opens the modal. Process their OOB content without replacing the main target. A disabled button may have been disabled by a model constraint before the request; it must remain so. Restore state after success and failure, including DOM replacements and aborted requests. Check links and menu entries, not just buttons, for export and switching. This is UI serialization of actions, not a new server authorization boundary.

## Validation

Run `npm run jest -- --runInBand js_tests/model_builder_main.test.js` and extend it with delayed/failing requests and pre-disabled controls. Run focused E2E `poetry run pytest tests/e2e/test_model_comparison.py --base-url http://localhost:8000` against a local server for model-switch/Compare regression; Task 9 adds the new autosave-specific browser case. The complete Jest/E2E suites remain the final gate.

## Out of scope

No field-save endpoints, draft queue, automatic retry or ordinary Modeling export warning for unsaved side-panel edits.

## Verified trigger paths

Model edits, creation/deletion, model switching and add/reset actions use HTMX requests; relationship-count inputs also autosave through HTMX. The toolbar's single-model and two-model download entries are plain `<a href>` links, while Compare uses an HTMX swap plus resident-canvas JS. Guard both HTMX mutation starts and link/menu activation; the existing per-XHR `WeakMap` restores surviving disabled buttons after requests, while swapped controls retain their server-rendered state.
