# Task 1 — Scope the save lock and retire the shared mutation lifecycle
Written 2026-10-14 against e-footprint-interface `ce018bf3` (with pre-existing unrelated local edits).
Plan: [one field save](../plan.html#save), [remove broad guard](../plan.html#cleanup), [verification](../plan.html#delivery). Task: [overview](../tasks.md#task-1).
Status: under review.

## Start here

- `saveEdit`, `initializeEdits`, `registerFieldEdits` — e-footprint-interface/`theme/static/scripts/simplified_inputs/field_edits.js` — value/provenance save, accepted `FormData` baseline and current shared-event consumer.
- `editor.html` form — `model_builder/templates/model_builder/simplified_inputs/editor.html` — add the plan's `hx-disabled-elt` selector here; the form already uses `hx-trigger="simplified-save"` and `hx-swap="none"`.
- Workspace guard IIFE, `saveCardOrder` — `theme/static/scripts/model_builder_main.js` — replace the former with the small disabled-state snapshot pattern visible in `git show main:theme/static/scripts/model_builder_main.js`; keep card-order persistence local.
- `registerWorkspace`, `registerBookmarks`, `hidePanelResult`, `sankeyRemoveCard` — `simplified_inputs/workspace.js`, `simplified_inputs/bookmarks.js`, `hammer_utils.js`, `sankey.js` — former shared-event consumers or emitters.

## Change along the code path

`saveEdit` validates and triggers the editor form. HTMX gathers form values, then `hx-disabled-elt` disables `button` and `input/select/textarea` inside every `[data-simplified-workspace]`, including the parked slot. Match the plan's exact selector and verify the submitted `FormData` still contains the initiating value. Restore only genuinely disabled native controls after HTMX releases its temporary attributes; do not force disabled state onto OOB replacement nodes that already carry server constraints.

Move field-save Saving/Saved/Not saved, quick-total busy feedback and accepted baselines to matching HTMX lifecycle events in `field_edits.js`. Account for `htmx:afterRequest` preceding possible OOB `htmx:afterSettle`; the accepted form may have replaced the request form. For a transport failure there may be no swap, yet `data-saving` and status still need release. Keep focused timeseries success/failure status and panel closure locally owned. `_rejected_simplified_input` in `model_builder/adapters/views/views_simplified_inputs.py` already returns accepted editor fragments and an error modal; the view is unchanged.

Delete the broad capture listeners, `body.dataset.workspaceMutation`, shared events and fetch entry/exit emitters. `workspace.js` matches its Configure form's HTMX outcome for pending Save/Discard/Stay continuation, and pending reads still abort when their actual target/request requires it. Bookmarks retain their own `htmx:afterRequest` result handling and local Saving status. Source editor focusout no longer checks global busy. Card order and Sankey deletion keep their existing `fetch`/response behavior without a shared bus. `hidePanelResult` locally waits for a pending response that can still update its result target before detaching it.

## Earlier tasks

None. Task 2 consumes the absence of the global flag and the scoped editor lock; it removes the export listener's obsolete busy branch and adapts export-specific evidence.

## Reuse

- Vendored `theme/static/scripts/external_librairies/htmx.min.js` has `hx-disabled-elt` request counting and removes its disabled attributes before `htmx:afterRequest`; the former helper on `main` snapshots initially disabled buttons by XHR.
- `savedEdits`, `editSnapshot`, `setSaveStatus` and existing field-form `data-value-prefix` identify the accepted replacement; `js_tests/build_fixtures.py` renders the real editor template for Jest fixtures.
- Existing local HTMX listeners in `workspace.js` already match pending read XHRs; `bookmarks.js` already owns patch response and Undo; `tests/e2e/utils.py` waits for request and swap settling.

## Invariants and traps

- `FormData` omits disabled controls. Snapshot accepted OOB forms only after temporary HTMX disabling ends, and never treat a disabled payload as accepted.
- Do not remove the independent unsaved side-panel/Configure confirmation, server rejection restoration or existing constraint-disabled state. An ordinary Modeling/Configure/bookmark/card-order action no longer promises global serialization.
- Replace assertions of `body[data-workspace-mutation]` in `tests/e2e/test_simplified_inputs.py`, `tests/e2e/test_model_comparison.py` and shared Playwright waits. The comparison tests currently assert old global blocking for relationship-count and object-deletion requests; test their retained local behavior instead of preserving the obsolete contract.

## Validation

- `npm run jest -- --runInBand js_tests/model_builder_main.test.js js_tests/simplified_inputs.test.js js_tests/simplified_bookmark_lifecycle.test.js` from e-footprint-interface. Retire tests for global capture/anchor stripping; retain meaningful prerequisite restoration, card-order fetch, bookmark feedback, accepted snapshot and local completion checks.
- `npm run build:js:dev`, then focused `poetry run pytest tests/e2e/test_simplified_inputs.py tests/e2e/test_model_comparison.py -n 4 --base-url http://localhost:8000` with the local server. In a delayed field save assert one request with submitted value, all relevant native controls disabled in both slots, rejected/transport outcomes usable again, and prerequisite-disabled controls still disabled. Check Configure continuation, bookmark feedback and closing Results while a Sankey response is pending.
- Task 2 runs the complete repository gates after export cases and documentation are updated.

## Out of scope

No new queue/retry, cross-tab coordination, server persistence change, or guarantee that Modeling and Configure writes serialize. Export behavior and document reconciliation belong to Task 2.

## Unverified

No product-design unknown remains. The exact OOB event order and transport-error shape must be exercised in browser tests against the vendored HTMX runtime; Jest's synthetic events alone cannot establish that timing.
