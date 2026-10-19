# Request lifecycle simplification — tasks

Spec: [spec.html](spec.html) · Plan: [plan.html](plan.html)
Status: under review. All plan amendments are decided.

## Implementation runs

| Run | Delivered milestone | Tasks in execution order | Prerequisites |
|---|---|---|---|
| A | One completion signal across the interface. Field and bookmark saves are rendered by the server. Reads and exits only block. Results close at once. Docs and changelog match. | [1](#task-1--platform-signal-and-button-locks) → [2](#task-2--declarative-field-saves) → [3](#task-3--bookmark-fragments) → [4](#task-4--reads-exits-results-close-and-close-out-docs) | Approval of this breakdown |

## Overview

| Task | Delivered behavior | Plan section | Repository | Implementation |
|---|---|---|---|---|
| [1](#task-1--platform-signal-and-button-locks) | HTMX settles before `afterRequest`. Button locks skip already disabled controls, so the global restore block goes. The conventions rule and test helpers match. | [1.1](plan.html#platform), [delivery A](plan.html#delivery) | e-footprint-interface | easy — one config flag, a mechanical selector replacement with a clear mapping, and deleting a self-contained block |
| [2](#task-2--declarative-field-saves) | The field editor is declarative. Saved and Not saved are rendered by the server, Saving… and Updating… come from CSS, the user-data rule runs on the server, and the notice is a fragment. `field_edits.js` is removed. | [1.2](plan.html#field-save) | e-footprint-interface | standard — combines established HTMX attributes, an existing out-of-band renderer and a small use-case rule. It needs ordinary care with trigger filtering and indicator CSS. |
| [3](#task-3--bookmark-fragments) | The bookmark patch answers with out-of-band HTML for every mounted instance. Undo, the JSON reconciler and lock refresh are removed. | [1.3](plan.html#bookmarks) | e-footprint-interface | standard — a new fragment template and view response built from an existing context builder, with a defined instance-matching rule |
| [4](#task-4--reads-exits-results-close-and-close-out-docs) | Reads switch the view on click and replace each other. Each slot remembers its own view. The dirty Configure gate only blocks. The Results chevron is a lockable button and closing is immediate. Architecture docs and the changelog match. | [1.4](plan.html#exits), [1.5](plan.html#results) | e-footprint-interface | standard — mostly removal toward sketched code. Gate and E2E rewrites need ordinary care with focus and request timing. |

## Plan amendments to review

[Amendment index in the plan](plan.html#plan-updates)

- [PLAN-UPDATE-09](plan.html#plan-update-09): ACCEPTED, integrated into Task 1.
- [PLAN-UPDATE-10](plan.html#plan-update-10): REJECTED; a changed value keeps its confidence (spec accepted change). Affects Task 2.
- [PLAN-UPDATE-11](plan.html#plan-update-11): SUPERSEDED by PLAN-UPDATE-12.
- [PLAN-UPDATE-12](plan.html#plan-update-12): ACCEPTED; the view is remembered on the slot element (spec accepted change). Affects Task 4.

## Task 1 — Platform signal and button locks

Goal: Make `htmx:afterRequest` mean "DOM final" everywhere and stop HTMX re-enabling prerequisite-disabled controls, with no client restore step.

Status: under review

Brief: [briefs/task-1.md](briefs/task-1.md)

Repository: `e-footprint-interface` only.

Files touched: `theme/templates/base.html`; `model_builder/templates/model_builder/simplified_inputs/editor.html`. Every template declaring `hx-disabled-elt="button"` (about 40 files under `model_builder/templates/`). `theme/static/scripts/model_builder_main.js`; `js_tests/model_builder_main.test.js`; `tests/e2e/utils.py`; `specs/conventions.md`; `specs/testing.md`; `specs/architecture/rendering.html` ("Scoped field-save disabling" and the bundle-order sentence).

Tests: Remove the three restore-block Jest cases. Run the full Jest, Python and E2E suites against rebuilt assets. This full green run is the evidence that synchronous settle breaks nothing.

Acceptance:

- `base.html` declares `<meta name="htmx-config" content='{"defaultSettleDelay": 0}'>` next to the HTMX script.
- No `hx-disabled-elt` selector can match an already disabled control. The editor uses the plan's `:not(:disabled)` selector, and every plain `button` selector becomes `button:not(:disabled)` (PLAN-UPDATE-09).
- The `model_builder_main.js` disabled-state snapshot and restore block is gone, along with its Jest cases. During a delayed field save, `#compare-tab` and a gated Add button stay disabled afterwards.
- `click_and_wait_for_htmx()` and `wait_for_htmx_idle()` wait on the request class only.
- `conventions.md` carries the PLAN-UPDATE-06 rule as an explicit prohibition and drops "listener order is part of mutation settlement". `testing.md` and the two `rendering.html` passages say settling classes never persist.
- Full Jest, Python and E2E suites pass with no other feature change.

Depends on: none.

Implementation: easy — one config flag, a mechanical selector replacement with a clear mapping, and deleting a self-contained block. The full-suite run is verification breadth, not design work.

## Task 2 — Declarative field saves

Goal: Replace `field_edits.js` with HTMX attributes, a server-rendered outcome and CSS, keeping the field-save behavior the spec preserves.

Status: under review

Brief: [briefs/task-2.md](briefs/task-2.md)

Repository: `e-footprint-interface` only.

Files touched: `model_builder/templates/model_builder/simplified_inputs/{editor,field,workspace,timeseries_panel}.html`; `model_builder/adapters/presenters/simplified_inputs.py`; `model_builder/adapters/views/views_simplified_inputs.py`; `model_builder/application/use_cases/simplified_inputs.py`; `theme/static/scss/_simplified_inputs.scss` with recompiled `theme/static/css/bs_main.css`; `theme/static/scripts/simplified_inputs/{index.js, field_edits.js (removed)}`; `js_tests/{simplified_inputs,dynamic_forms}.test.js`; `js_tests/build_fixtures.py`; view tests; `tests/e2e/test_simplified_inputs.py`; `specs/conventions.md` (module list); `specs/architecture/rendering.html` (repair-notice paragraph).

Tests: View tests for the per-field outcome, the notice fragment, resent provenance as a no-op, and the user-data rule, including a changed value keeping its confidence. E2E for trigger counts, delayed-save probes using the request class, transport failure leaving an empty status, the timeseries panel closing, and the multiple-select flow. Remove the field-save Jest cases.

Acceptance:

- The editor form declares its trigger, sync, values, indicator, validation and lock as in the plan. No feature JavaScript listens for field-save events.
- A blur without an edit, or retyping the original value, sends nothing. A changed blur, Enter, a select change, a provenance change and the empty switch each send one request. Enter followed by blur sends once.
- An invalid draft sends nothing and shows the browser message.
- Saving… and Updating… appear only while the request class is present. Saved, which fades, and Not saved arrive on the submitted field only. An unanswered request leaves an empty status, enabled controls and a working next edit.
- A changed value whose source is a hypothesis or automatic replacement saves as user data, keeping its comment and confidence. Provenance-only saves keep the source.
- The repair notice renders as an out-of-band `#si-{system_id}-notice` paragraph, and no `simplifiedInputSaved` trigger remains. The export notice writes into the same paragraph.
- The timeseries panel closes after either outcome, its Cancel sends no request, and it sends `recomputation` when Results is open.

Depends on: Task 1.

Implementation: standard — combines established HTMX attributes, an existing out-of-band renderer and a small use-case rule. It needs ordinary care with trigger filtering and indicator CSS.

## Task 3 — Bookmark fragments

Goal: Make the bookmark patch endpoint return rendered fragments for every mounted instance, and drop the client reconciler and Undo.

Status: under review

Brief: [briefs/task-3.md](briefs/task-3.md)

Repository: `e-footprint-interface` only.

Files touched: `model_builder/templates/model_builder/simplified_inputs/{bookmark,bookmark_controls}.html`; new `{bookmark_summary,bookmark_status,bookmark_update}.html`; `model_builder/adapters/views/views_simplified_inputs.py`; `theme/static/scripts/simplified_inputs/bookmarks.js`; `js_tests/{simplified_bookmark_lifecycle,simplified_inputs}.test.js`; `js_tests/build_fixtures.py` if needed; view tests; `tests/e2e/test_simplified_inputs.py`; `specs/architecture/{forms-and-relationships,runtime-and-recovery}.html`; `specs/testing.md` (Undo sentences).

Tests: Replace `test_bookmark_patch_and_inverse_preserve_values_and_retained_help` with fragment assertions, and add a rejection-status case. Jest checks the request payload. Adapt the E2E flows for failed help and membership.

Acceptance:

- The request carries `patch` plus `mounted` ids and nothing from the surrounding form. Creation panels still send `simplified_settings`.
- The response renders a summary and controls only for mounted instances of affected addresses, with Saved only on the `HX-Trigger` instance.
- 422 and 500 keep the modal and add one Not saved status fragment.
- No Undo button, inverse patch, `pendingUndo`, JSON reconciler or `refreshBookmarkLocks` remains.
- After a failed help save, a successful membership save replaces the help with the saved text.

Depends on: Task 2 (shared "Saving…" rule and outcome-status pattern).

Implementation: standard — a new fragment template and view response built from an existing context builder, with a defined instance-matching rule

## Task 4 — Reads, exits, Results close and close-out docs

Goal: Make saved-view reads and Configure exits use HTMX's request replacement and a gate that only blocks, close Results at once, and reconcile the remaining docs and the changelog.

Status: under review

Brief: [briefs/task-4.md](briefs/task-4.md)

Repository: `e-footprint-interface` only.

Files touched: `theme/static/scripts/simplified_inputs/workspace.js`; `model_builder/templates/model_builder/model_builder_main.html`; `tests/unit_tests/adapters/views/test_views_simplified_inputs.py` (opening-default assertion); `theme/static/scripts/hammer_utils.js`; `model_builder/templates/model_builder/result/result_panel.html`; `js_tests/{simplified_inputs,model_builder_main}.test.js`; `tests/e2e/{test_simplified_inputs.py,pages/model_builder_page.py}`; `specs/architecture/{workspace,rendering}.html`; `CHANGELOG.md`.

Tests: Jest cases for the gate only and for the read entry. E2E: invert the abandoned Configure read test, add a saved-view late-read variant, update the repeated-entry, dirty-exit and Configure-save-failure tests, extend the base-view test with a rebuild, and rewrite the two Results close tests.

Acceptance:

- Entering Simplified, Configure or Discard closes the side panel, switches the view and sends one replaceable read. A double click on Configure renders one form that is not replaced afterwards.
- A late read lands in its slot and is shown on return, including Configure.
- A dirty Configure blocks every shared exit with Save, Discard and Stay and issues no request. Save and Discard show the saved view only, and a second click reaches the destination.
- No `pendingRead`, `pendingExit`, `replaying`, `savingRequest`, `deferExit` or swap/settle listener remains.
- Each slot carries its view as `data-view`, rendered by the server and written by `setBaseView()`. Switching models restores each model's view; a builder rebuild opens each model in its default view. No `viewBySystemId` map or empty-slot re-read remains.
- Both Results close controls are disabled during a delayed save. Closing empties the panel at once, even during a Sankey load.
- `workspace.html` and `rendering.html` describe the accepted rules. `CHANGELOG.md` has one Changed entry covering the behavior trades, including the Undo removal.

Depends on: Task 1. The changelog and the rest of the reconciliation also depend on Tasks 2 and 3.

Implementation: standard — mostly removal toward sketched code. Gate and E2E rewrites need ordinary care with focus and request timing.

## Gates and prerequisites

- **Blocks implementation:** approval of this breakdown only; every plan amendment is decided.
- **Blocks later tasks:** Task 1's full green E2E run against rebuilt assets is the evidence for synchronous settle. Tasks 2 to 4 rely on it. Run against a local `runserver` from this checkout with `npm run build:js:dev` and the compiled SCSS.
- **No other gate:** no migration, library change or serialization change. `pyproject.toml` already pins PyPI `efootprint`.
- **Follow-up, not part of this run:** the constitution §1.4 sentence through `update-constitution` (decision 10), and the parked `htmx-aware-server-error-handler` backlog item.
