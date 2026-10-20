# Task 5 — Reads lock like saves
Written 2026-10-20 against `e-footprint-interface` commit `b739aca6` (run A delivered).
Plan: [1.4 Reads and exits](../plan.html#exits), [PLAN-UPDATE-13](../plan.html#plan-update-13) (accepted), [IMPL-DECISION-03](../plan.html#impl-decision-03).
Task: [Task 5](../tasks.md#task-5--reads-lock-like-saves).
Status: under review.

## Start here
- The slot `<div data-simplified-target>` — `model_builder/templates/model_builder/model_builder_main.html` line 19: carries `hx-sync="this:replace"` today.
- `loadView()` — `theme/static/scripts/simplified_inputs/workspace.js` line 36: issues the read with `htmx.ajax(..., {source: target})`, so HTMX reads `hx-disabled-elt` on the slot and puts the request class on the slot.
- The field editor's lock selector — `model_builder/templates/model_builder/simplified_inputs/editor.html` line 10.
- `[data-simplified-save-status]` rules — `theme/static/scss/_simplified_inputs.scss` (around line 80), for where the loader rule goes.
- E2E held-read tests — `tests/e2e/test_simplified_inputs.py`: `test_repeated_configure_entry_renders_one_form_that_keeps_its_draft` (line 156), `test_late_read_lands_in_its_slot_and_is_shown_on_return` (line 185), `test_model_base_views_survive_switch_and_compare` (line 319).

## Change along the code path
1. **Slot.** Remove `hx-sync`. Add `hx-disabled-elt="button:not(:disabled), [data-simplified-workspace] input:not(:disabled), [data-simplified-workspace] select:not(:disabled), [data-simplified-workspace] textarea:not(:disabled)"`, the editor's selector verbatim. Verify in the vendored HTMX 2.0.6 that `htmx.ajax` with `source` honours `hx-disabled-elt` on the source and adds `htmx-request` to it (it does for `hx-indicator`; confirm for the disabled handling, which reads the closest attribute from the requesting element).
2. **Loader.** One rule block on `[data-simplified-target].htmx-request`: dim the content (for example `opacity` on the children or the slot) and show a centred Bootstrap `spinner-border` through `::before`/`::after`, matching the spinner the Results panel already uses (`result/sankey_card.html`). `pointer-events: none` on the slot's children is a belt-and-braces addition; the lock is the mechanism. Recompile `bs_main.css` and its map.
3. **Configure form.** Keep its own lock from IMPL-DECISION-03 unchanged. HTMX takes the closest declaration, so the slot's selector does not override it during a Save.
4. **Scripts.** `workspace.js` keeps its logic; rewrite the header comment that mentions `hx-sync` to describe the lock. Nothing else in JS changes.
5. **Docs.**
   - `specs/conventions.md`: add a bullet after the "Feature JavaScript does not anticipate…" bullet: *User-initiated requests are sequential.* Every element that issues a navigation or mutation request declares `hx-disabled-elt="button:not(:disabled)"` (plus the workspace controls for Simplified inputs), so one user action completes before the next can start; never use `hx-sync`, pending flags, queues or replacement rules to arbitrate between user actions. `hx-sync="this:drop"` on a single element is allowed only to dedupe its own duplicate triggers. Background requests (timeseries previews, metadata autosaves, workspace-storage polls, Sankey and lazy loads) stay unlocked and must target only their own region. Note that elements outside Simplified inputs still missing the lock are a separate follow-up.
   - `specs/architecture/workspace.html`: the read passage describes the lock and loader; delete the request-replacement sentences and the "late read lands after a model switch" rule; the Configure-Save paragraph loses its inheritance explanation (the lock is simply the standard save lock).
   - `specs/architecture/rendering.html`: same for any sentence on reads replacing each other.
   - `CHANGELOG.md`: in the feature's consolidated Changed entry, replace "the fresh read replaces the slot when it lands, including after a model switch" with wording that reads lock the interface behind a loader until they land.

## Earlier tasks
Task 4 built `loadView`, `setBaseView`, the blocking gate and the Configure lock. Nothing in the gate changes: a dirty Configure still blocks before any request.

## Reuse
The editor's lock selector; the Results spinner markup; `wait_for_htmx_idle()` and the `page.route` hold pattern already used in the held-read tests.

## Invariants and traps
- Do not resume navigation, do not store requests, do not re-read empty slots (PLAN-UPDATE-05, -06, -12).
- Check every non-button way to switch models or issue a read during a held read: model tabs and the active-model role are `<button>`s; links and keyboard shortcuts are not locked. If one remains, keep `test_late_read_lands_in_its_slot_and_is_shown_on_return` for that path and say so; otherwise delete it and the matching sentence in the docs.
- The slot's lock locks the stale workspace's inputs too, so a blur in the stale content cannot start a field save during a read.
- Decision 4's accepted edge (a control locked by another request is released early) still applies when a background request overlaps; do not add anything for it.

## Validation
- **E2E:** rewrite `test_repeated_configure_entry_renders_one_form_that_keeps_its_draft` so the double click yields exactly one request (the second click hits a disabled button). Add a held entry read case asserting the slot has the request class, the Configure button, the toolbar Simplified toggle and `#model-tab-*` buttons are disabled, and that all are enabled after release with the saved view rendered. Keep `test_model_base_views_survive_switch_and_compare` green.
- **Jest:** grep `js_tests/` for `hx-sync` and adjust fixtures or assertions only if one names it.
- **Commands:** `npm run build:js:dev`, compile the SCSS, `npm run jest`, `poetry run pytest tests --ignore=tests/e2e`, then `poetry run pytest tests/e2e -n 4` against a local server from this checkout.

## Out of scope
Applying the lock to request-issuing elements outside Simplified inputs (model tabs' own attributes, side-panel membership buttons, Results controls and the like): that sweep is a separate batch once the convention is agreed.

## Unverified
Whether `hx-disabled-elt` applies to `htmx.ajax` requests issued with `source` under HTMX 2.0.6. The implementer verifies it in `htmx.min.js` before relying on it; if it does not, pass the selector through the `htmx.ajax` call options or fall back to the slot's `hx-disabled-elt` read via `getClosestAttributeValue`, and report which.
