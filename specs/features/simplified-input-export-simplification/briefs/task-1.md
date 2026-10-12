# Task 1 — Replace export continuation with saved-state admission

Written 2026-10-12 against `e-footprint-interface` commit `07fac466497e63bb8b54ee54183fc91f9665939f` and its current working-tree plan. Existing middleware/dependency edits are outside scope.
Plan: [Activation](../plan.html#activation) · [Configure](../plan.html#configure) · [Verification](../plan.html#delivery).
Task: [Task 1](../tasks.md#task-1--replace-export-continuation-with-saved-state-admission).
Status: under review.

## Start here

- `continueExport`, composition and capture handlers — `theme/static/scripts/simplified_inputs/index.js`: all external export replay ownership.
- `createFieldEdits`, `completeFocusedEditForExport`, `saveEdit`, both `workspace-mutation:finished` listeners — `theme/static/scripts/simplified_inputs/field_edits.js`: remove only export coordination; keep accepted snapshots, status and timeseries closure.
- `createWorkspace`, `registerWorkspace`, `deferExit`, `replayClick` — `theme/static/scripts/simplified_inputs/workspace.js`: exempt export controls before cancellation/deferral; retain internal replay for other exits.
- `mount`, `mountEditor` and export cases — `js_tests/simplified_inputs.test.js`; `render_simplified_workspace`, `render_simplified_editor` — `js_tests/build_fixtures.py`.

## Change along the code path

Remove export-specific `mousedown` focus preservation, focused completion, `pendingExport`, `continueExport` and the editor's callback parameter/API. Keep ordinary numeric focusout/Enter, provenance changes and validation in `saveEdit`. In the existing window-capture export listener, return during a shared write; otherwise inspect `workspace.configureForm()?.dataset.dirty`. Dirty Configure prevents default and stops immediate propagation before Bootstrap; inline the existing paragraph/status notice pattern after the active workspace's `.simplified-header` with `data-simplified-notice`. Replace any previous notice. Use the exact plan feedback text.

Add `[data-workspace-export]` to the generic Configure capture exclusion, including descendants, before `cancelPendingRead()` and `deferExit()`. Clean Configure thus keeps native download/menu behavior without a saved-view GET. Remove unused entry-point destructuring and workspace return entries `replayClick`/`isReplaying`; keep internal replaying, `pendingExit`, `deferExit` and save-settlement navigation for non-export destinations.

## Earlier tasks

None. Implement against the current shared lock; the mutation-gate redesign comes later.

## Reuse

- `registerConfiguration` — `configuration.js`: existing form-level dirty flag; no new baseline.
- `source_metadata.js` focusout handler / `applySourceEditor`: named hidden provenance fields and `simplified-provenance:changed` trigger; no export changes here.
- Shared-guard IIFE `begin`, `finish`, `lockControls` — `model_builder_main.js`; `startMutation`/`completeMutation` tests in `js_tests/model_builder_main.test.js`. Load the actual guard for busy tests; a mocked HTMX save trigger alone does not prove locking.
- `_single_model_document`, `download_json`, `download_workspace` — `model_builder/adapters/views/views.py`: accepted repository-state export. `_rejected_simplified_input` and `save_simplified_inputs` — `views_simplified_inputs.py`: existing rejected-field restoration and Configure lifecycle; no Python edits planned.

## Invariants and traps

Keep synchronous registration before `model_builder_main.js`. The export listener must stay at window capture before Bootstrap document capture. Do not suppress native blur or call `reportValidity()` from export; ordinary save owns validation. Keep initialization after unlock because FormData omits disabled inputs. The second finished listener also closes timeseries panels on success/failure; do not delete it wholesale. Failed Configure save retains dirty state; success/discard removes the notice by replacing the workspace. Native control disabling and link destination removal remain shared-guard responsibilities.

## Validation

Replace focused-export tests, including rejected, invalid, press/direct activation cases. Explicitly dispatch ordinary focusout/Enter/provenance events; assert one save, no settlement replay and native idle activation. Test all marked controls in clean/dirty Configure, nested click targets, one replaced notice, no GET/save/dialog, no continuation after successful/failed settlement or discard. Retain non-export Stay/Save continuation, accepted-field restoration and timeseries closure cases. Extend named rendered fixtures for Configure plus toolbar if needed; never hand-roll real template markup. Reuse guard test stubs without registering duplicate persistent listeners.

From the interface root: `npm run jest -- --runInBand js_tests/simplified_inputs.test.js js_tests/model_builder_main.test.js`, then `npm run jest`. The npm wrapper renders fixtures through the configured Poetry environment. Task 2 owns actual focus/Bootstrap/download verification and rebuilt assets; Jest cannot prove native focus ordering.

## Out of scope

Shared lock redesign/read cancellation changes, export queue/retry, new notice abstraction/control, server/file-format/library changes, unrelated local edits.

## Unverified

Full application focus and download behavior remains Task 2's required verification. Plan diagnostics support ordering but do not replace browser regressions. No design uncertainty remains from this code pass.
