# Task 4 — Reads, exits, Results close and close-out docs
Written 2026-10-19 against `e-footprint-interface` commit `e34a9bb3`.
Plan: [1.4 Reads and exits](../plan.html#exits), [1.5 Results close](../plan.html#results), [PLAN-UPDATE-03](../plan.html#plan-update-03), [-05](../plan.html#plan-update-05), [-08](../plan.html#plan-update-08), [-12](../plan.html#plan-update-12), [decisions 1, 7, 8](../plan.html#decisions).
Task: [Task 4](../tasks.md#task-4--reads-exits-results-close-and-close-out-docs).
Status: under review.

## Start here
- `createWorkspace` — `theme/static/scripts/simplified_inputs/workspace.js`: `viewBySystemId`, `setBaseView`, `loadView`, `initialize`, `deferExit`, `replayClick`, `finishConfigureSave`, and `registerWorkspace`'s capture click, `htmx:confirm`, action switch and lifecycle listeners.
- The `[data-simplified-target]` slot `<div>` — `model_builder/templates/model_builder/model_builder_main.html` (line 19), and `opening_default` in `model_builder/adapters/views/views.py` (around line 144).
- `hidePanelResult`, `pendingResultRefreshes` — `theme/static/scripts/hammer_utils.js`.
- The chevron `<div onclick="hidePanelResult()">` — `model_builder/templates/model_builder/result/result_panel.html` (line 8).
- `close_result_panel` — `tests/e2e/pages/model_builder_page.py`.

## Change along the code path
1. **Slot.** Add `hx-sync="this:replace"` to the slot `<div>`. `htmx.ajax(..., {source: target})` reads it at request time. Replace `data-opening-default` with `data-view="{{ slot_entry.opening_default|default:'modeling' }}"`. `views.py` only sets `simplified` when it also renders the workspace, so a Simplified slot from the server always has content.
2. **Reads and view memory (PLAN-UPDATE-12).** `loadView(configure)` is the plan sketch: guard the target, run `runAfterSidePanelDiscardConfirmation`, close the side panel, `setBaseView("simplified")`, send the read. `setBaseView(mode)` writes `target.dataset.view = mode` instead of the map. `initialize()` keeps `refreshSelection` for new workspaces and then calls `setBaseView(target.dataset.view || "modeling")` for the active slot; it never reads. Delete `viewBySystemId`, the `openingDefault` copy, the empty-slot `loadView(false)`, `pendingRead`, `cancelPendingRead` and the cancellation at the top of `initialize()`.
3. **Gate.** Use the plan's `blockWhileDirty(event)`. The capture click handler keeps its element matching (lines 135 to 138); delete the pending-read branch and `replaying`, then call `blockWhileDirty(event)`. A clean Configure is no longer intercepted. The `htmx:confirm` handler keeps its exclusions, minus `replaying`, then calls `blockWhileDirty(event)`. `preventDefault` there cancels the request.
4. **Action switch:**
   - `simplified-mode`: collapse the navbar, then `baseView === "simplified" ? setBaseView("modeling") : loadView(false)`. Reaching it while dirty is impossible, because capture blocked it.
   - `simplified-configure`: `loadView(true)`.
   - `simplified-cancel`, `-exit-save`, `-exit-discard`, `-exit-stay`: as in the plan sketch.
5. **Delete** `pendingExit`, `savingRequest`, `replayClick`, `deferExit`, `finishConfigureSave`, the four `htmx:beforeRequest`/`beforeSwap`/`afterRequest`/`afterSettle` listeners and the dialog `cancel` listener. Keep `beforeunload`, the three `initialize` hooks, `viewBySystemId`, `setBaseView` and `refreshSelection`. Drop `deferExit` from the returned object. Rewrite the header comment to describe view memory and the blocking gate.
6. **Results.** Make the chevron a `<button type="button" class="btn btn-link …" aria-label="Close results" onclick="hidePanelResult()">` with the same SVG, and keep the column classes on a wrapper. In `hammer_utils.js`, delete `pendingResultRefreshes` and its two listeners, `hasPendingResponse` and `finishClosing`. `hidePanelResult()` resets the layout and empties the panel unconditionally. Keep the `htmx:afterSettle` layout re-apply hook.
7. **Docs and changelog:**
   - `specs/architecture/workspace.html`: replace lines 50 to 51, 72 and 76 to 77 with the accepted rules (the spec as amended by PLAN-UPDATE-03, -05, -08 and -12). Line 48's "remembers only the last base view by System ID" becomes "each slot carries its last base view".
   - `specs/architecture/rendering.html`: rewrite "Results close safely" (close at once, chevron lockable, swipe edge accepted) and "Independent actions" (no continuations; bookmark feedback is server-rendered).
   - `CHANGELOG.md` `## [Unreleased]` → `### Changed`: add one entry covering every accepted behavior trade in the spec, including the Undo removal, the empty status on unanswered requests, no exit resume, view switching on click, native validation messages, and a changed value keeping its confidence.
   - `specs/mission.md` already has the "Guards block" rule; do not edit it.

## Earlier tasks
- Task 1: settle is synchronous, every button lock skips disabled buttons (PLAN-UPDATE-09), and the request-class E2E helpers are in place. Field and side-panel saves therefore disable the new chevron button because it is enabled.
- Task 2: `index.js` exports only `{ workspace }`, and the export notice writes into the rendered `[data-simplified-notice]`. The capture handler's `[data-workspace-export]` exclusion stays.
- Task 3: no bookmark lifecycle listeners remain, so "Independent actions" can say feedback is server-rendered.

## Reuse
`runAfterSidePanelDiscardConfirmation` and `closeAndEmptySidePanel` (`side_panel_utils.js`), the exit dialog in `exit_dialog.html`, and the existing `mount()` helper and fixtures in `js_tests/simplified_inputs.test.js`.

## Invariants and traps
- Do not resume any interrupted navigation (PLAN-UPDATE-05; mission rule).
- Do not store request objects or compare "did it swap". A read answered by an error leaves its slot empty or stale (PLAN-UPDATE-06).
- A Simplified slot without content means a read in flight or a failed read. `initialize()` must not fetch or retry in that case (PLAN-UPDATE-06, -12).
- The two-model Export toggle and the Results open button keep their current disabling. Only the close path changes.
- Do not abort a Sankey request on close (decision 7). One ECharts size warning is accepted.

## Validation
- **Jest** (`js_tests/simplified_inputs.test.js`): replace the import of `deferExit` and the cases "duplicate pending reads are suppressed…", "Stay keeps the draft and Save resumes…", "internal saved-view reads bypass exit interception…", "%s resolves Configure explicitly without continuing an export" and "clean Configure export does not cancel a pending saved-view read". New cases:
  - entering switches `data-base-view` before any response, with one `htmx.ajax` call whose `source` is the slot;
  - a dirty Configure blocks a toolbar click and an `htmx:confirm`, opens the dialog and issues no request;
  - Save calls `requestSubmit`, Discard calls one read, and Stay issues nothing;
  - none of them replays the click;
  - a clean Configure exit is not intercepted.
  - with two slots, `switchModelCanvas` applies each slot's `data-view`, and an empty Simplified slot triggers no `htmx.ajax` call.
- **Jest** (`js_tests/model_builder_main.test.js`): replace "closing Results waits for its pending response…" with one case that closing during a pending recomputation empties `#result-block` at once.
- **E2E** (`tests/e2e/test_simplified_inputs.py`):
  - `test_repeated_configure_entry_does_not_queue_a_draft_replacement`: double-click Configure, then one form whose draft survives.
  - `test_abandoned_configure_read_cannot_follow_a_model_switch`: invert it so the late Configure response is shown on return, rename it, and add a saved-view variant.
  - `test_dirty_configure_protects_every_shared_exit`: Discard shows the saved view without reaching the destination, and a second click reaches it.
  - `test_configure_save_failure_retains_the_draft_and_exit_guard`.
  - The two `test_closing_results_waits_…` tests: rename them; both close controls are disabled during a delayed save, and closing during a delayed Sankey load empties the panel and nothing re-opens it.
  - `test_model_base_views_survive_switch_and_compare` stays green; extend it so that after Duplicate a model left in Simplified opens in Modeling. Re-run `test_mode_change_uses_existing_unsaved_panel_warning` and `test_json_selected_opening_and_fresh_render_after_modeling_edit`.
  - View test `test_json_opening_defaults_are_applied_once_independently_per_slot`: assert `data-view="simplified"` on the first render and `data-view="modeling"` on the next.
  - In the page object, `close_result_panel` selects `get_by_role("button", name="Close results")`.
- **Commands:** `npm run build:js:dev`, `npm run jest`, `poetry run pytest tests --ignore=tests/e2e`, then `poetry run pytest tests/e2e -n 4` against a local server running this checkout.

## Out of scope
- Side-panel unsaved-changes guards and their replay (in the follow-up note).
- Sankey and card-order fetches, model comparison, and tour hooks.
- The export interception in `index.js`, beyond what Task 2 changed.
- The constitution §1.4 amendment.

## Unverified
None material. The touch swipe-down during a save is an accepted edge (decision 1) and needs no test.
