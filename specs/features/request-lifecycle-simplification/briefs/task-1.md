# Task 1 — Platform signal and button locks
Written 2026-10-19 against `e-footprint-interface` commit `e34a9bb3`.
Plan: [1.1 Platform](../plan.html#platform), [delivery step A](../plan.html#delivery), [PLAN-UPDATE-06](../plan.html#plan-update-06), [PLAN-UPDATE-09](../plan.html#plan-update-09) (accepted).
Task: [Task 1](../tasks.md#task-1--platform-signal-and-button-locks).
Status: under review.

## Start here
- `theme/templates/base.html` — the HTMX `<script>` tag in `<head>`. The config meta tag goes immediately before or after it. HTMX reads it once at ready time, so either position works.
- The IIFE after the comment "HTMX releases hx-disabled-elt unconditionally" — `theme/static/scripts/model_builder_main.js`: the global snapshot/restore block that this task deletes.
- The `<form data-simplified-editor>` `hx-disabled-elt` attribute — `model_builder/templates/model_builder/simplified_inputs/editor.html`.
- `wait_for_htmx_idle`, `click_and_wait_for_htmx` — `tests/e2e/utils.py`.
- `js_tests/model_builder_main.test.js` — the three cases "HTMX button restoration does not overwrite control state…", "native disabling restores prerequisite controls…" and "overlapping HTMX requests distinguish temporary disabling…".

## Change along the code path
1. Add `<meta name="htmx-config" content='{"defaultSettleDelay": 0}'>`. HTMX 2.0.6 then runs settle inline in the swap, before lock release and `htmx:afterRequest` (plan 1.1 verification). After this, no project code observes a gap between swap and settle.
2. Editor lock: use the plan's selector, `button:not(:disabled), [data-simplified-workspace] input:not(:disabled), …select:not(:disabled), …textarea:not(:disabled)`.
3. PLAN-UPDATE-09: replace every `hx-disabled-elt="button"` with `hx-disabled-elt="button:not(:disabled)"`. That is 52 occurrences in about 40 templates; list them with `grep -rln 'hx-disabled-elt="button"' model_builder/templates theme/templates`. Leave the three `hx-disabled-elt="this"` declarations alone. A scripted `sed` is fine; afterwards verify the count of plain `"button"` is zero.
4. Delete the restore IIFE (both listeners) and its three Jest cases. The tests in `simplified_inputs.test.js` and `simplified_bookmark_lifecycle.test.js` require `model_builder_main.js` only for "listener ordering". Leave those requires for now: later tasks rewrite those files, and the module still registers other handlers.
5. `tests/e2e/utils.py`: both helpers wait on `.htmx-request` only. Drop `.htmx-settling, .htmx-added` and the "settled" comments. The other copies of that selector in page objects and tests are harmless (the classes never persist); remove them only where you are already editing.
6. Docs. In `specs/conventions.md`, the JavaScript bullet on line 26 loses "listener order is part of mutation settlement". Add a new bullet with the PLAN-UPDATE-06 text, worded as a prohibition, as the spec's maintainability outcome requires. Leave the `field_edits.js` module mention for Task 2. In `specs/testing.md` (HTMX interactions, around line 171), say that settling classes never persist and the helpers wait on the request class, and tell test authors to assert rendered outcomes rather than dispatch synthetic lifecycle sequences. In `specs/architecture/rendering.html`, rewrite "Scoped field-save disabling" (no restore, `:not(:disabled)`, synchronous settle) and the bundle-order sentence (line 60): order is no longer part of settlement.

## Earlier tasks
None. Field saves still run through `field_edits.js` in this task. With zero settle delay its four-listener bookkeeping still completes, because settle runs before `afterRequest`. That is the evidence this task produces.

## Reuse
The pattern of the existing `:not()`-free selectors; the HTMX selector resolution described in plan 1.1 (top-level comma splitting). No new helper.

## Invariants and traps
- Do not change the HTMX version or other vendored files (spec constraint).
- Decision 4's accepted edge: a control locked by another in-flight request is skipped and released early. Do not add a selector or listener that distinguishes it.
- `htmx:afterSettle` re-initialisation hooks (tooltips, charts, leader lines, `hammer_utils.js` layout) stay. They now run inside the swap.

## Validation
`npm run build:js:dev`; `npm run jest`; `poetry run pytest tests --ignore=tests/e2e`. Then start `poetry run python manage.py runserver` from this checkout and run `poetry run pytest tests/e2e -n 4`.
Check `test_field_save_disables_both_resident_workspaces_and_restores_controls`: `#compare-tab` must stay disabled after the save, with no restore script. Also check one gated-Add flow, such as a card action while an Add button is disabled. ERR_CONNECTION_RESET or timeouts under `-n 4` are transient; rerun them in isolation before treating them as real.

## Out of scope
Removing `field_edits.js` or any of its listeners (Task 2), bookmark and workspace listeners (Tasks 3 and 4), and the Results close wait (Task 4).

## Unverified
Whether any E2E flow relied on the 20 ms settle window. The full-suite run settles it; a failure reproducible in isolation is a real finding to report, not a reason to add waits.
