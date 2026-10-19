# Task 3 — Bookmark fragments
Written 2026-10-19 against `e-footprint-interface` commit `e34a9bb3`.
Plan: [1.3 Bookmarks](../plan.html#bookmarks), [PLAN-UPDATE-01](../plan.html#plan-update-01), [decisions 2 and 6](../plan.html#decisions).
Task: [Task 3](../tasks.md#task-3--bookmark-fragments).
Status: under review.

## Start here
- `patch_simplified_inputs` — `model_builder/adapters/views/views_simplified_inputs.py`: it keeps the affected-set computation and replaces the `JsonResponse`.
- `bookmark_context(model_web, address, *, catalog, definition, suffix)` — `model_builder/adapters/forms/simplified_input_context.py`. It yields `dom_id = bookmark-{owner}-{attribute}-{suffix}`; the suffix is `panel` or `sources`.
- `bookmark.html`, `bookmark_controls.html`, `selection_controls.html` — `model_builder/templates/model_builder/simplified_inputs/`.
- `registerBookmarks`, `updateBookmark`, `saveBookmark`, `refreshBookmarkLocks` — `theme/static/scripts/simplified_inputs/bookmarks.js`.

## Change along the code path
1. **Request.** `saveBookmark(bookmark, patch)` loses its `undo` argument and `pendingUndo`. The existing `htmx:configRequest` branch for `[data-bookmark]` keeps `patch` and adds `mounted`: a JSON list of the ids of every `[data-bookmark]:not([data-provisional-owner])` in the document. It is JSON, like `patch`. `hx-params="none"` filters before `configRequest`, so the payload stays exactly these two keys. The creation-time `simplified_settings` branch is unchanged.
2. **Templates.**
   - Extract `<summary>` into `bookmark_summary.html` with `id="{{ field.dom_id }}-summary"` and `{% if oob %}hx-swap-oob="outerHTML"{% endif %}`.
   - In `bookmark.html`, wrap the non-lazy controls in `<div id="{{ field.dom_id }}-controls">`; the lazy branch already has that container.
   - Move the status `<small>` into `bookmark_status.html` with `id="{{ field.dom_id }}-status"`, `data-bookmark-status`, `role="status"` and an optional out-of-band attribute, rendering "Saved" or "Not saved" from `outcome`.
   - Remove the Undo button from `bookmark_controls.html`.
   - Add the indicator `hx-indicator="find [data-bookmark-status]"` to the `<details>` (saved branch only).
   - New `bookmark_update.html`: the summary include with `oob=True`, plus `<div id="{{ field.dom_id }}-controls" hx-swap-oob="innerHTML">{% include bookmark_controls %}</div>`.
3. **Response.**
   - Drop `previous` and the inverse computation.
   - Read `mounted` as a set and the trigger id from `request.headers.get("HX-Trigger")`.
   - For each affected address, sorted as today, and each suffix in `("panel", "sources")`: build `bookmark_context(..., suffix=suffix, catalog=catalog, definition=current)`. When its `dom_id` is in `mounted`, render `bookmark_update.html` with `outcome="saved"` only when `dom_id == trigger`.
   - Return an `HttpResponse` of the concatenation. Do not add `append_workspace_storage_status`; the JSON path never had it.
4. **Rejection.** Both `render_exception_modal(..., status=422, preserve_workspace=True)` returns and the outer 500 append one `bookmark_status.html` with `oob=True`, `outcome="rejected"` and `field={"dom_id": trigger}` when the header is present, the same way `_rejected_simplified_input` appends after the modal. No model access is needed. Missing or malformed `mounted` stays a 422 like `patch`.
5. **Client removal.** Delete the `htmx:afterRequest` reconciler, the "Saving…" `htmx:beforeRequest` listener, the Undo click handler, `refreshBookmarkLocks` and its three hooks. `updateBookmark` survives only as a local helper called from `refreshCreationBookmarks` (provisional bookmarks); stop exporting it unless a test still needs it. Keep the toggle/lazy-open handler, the Enter-blurs-help handler, the `input` → `tagFormAsModified` hook and the scroll-into-view settle hook.
6. **CSS.** Reuse Task 2's "Saving…" `::after` rule by adding `[data-bookmark-status].htmx-request` to its selector, with the same text-hiding.
7. **Docs.** Drop the Undo sentences in `specs/architecture/forms-and-relationships.html` (line 71), `runtime-and-recovery.html` (line 51) and `specs/testing.md` (line 193). State that the patch answers with out-of-band fragments for mounted instances.

## Earlier tasks
- Task 1: settle runs before `afterRequest`, and no restore block exists.
- Task 2: the out-of-band outcome-status pattern (`data-outcome`, server text) and the `.htmx-request` "Saving…" rule with its `:empty` and fade exemptions in `_simplified_inputs.scss`. Extend that rule; do not add a second one.

## Reuse
`bookmark_context`, `catalog.dependents` affected-set expansion, `render_exception_modal`, the `render_to_string(..., request=request)` style of `render_input_fields_oob`, and the existing `SIMPLIFIED_BOOKMARK_CASES` fixtures in `js_tests/build_fixtures.py`.

## Invariants and traps
- The `<details>` is never replaced: its open state and lazy trigger survive. Its `data-saved-included` and `data-required-label` would go stale for saved bookmarks. Only removed code reads them for saved bookmarks, so drop `data-saved-included` and confirm with `grep` before keeping or dropping `data-required-label`. Provisional code sets that one itself.
- Every out-of-band element must have a mounted target, or HTMX logs `htmx:oobErrorNoTarget` (decision 6). Lazy `sources` bookmarks have their `-controls` container from the first render, so pre-filling it is fine.
- Accepted trade (decision 2): a failed help draft is overwritten by the next successful fragment. Do not add a draft check.
- Controls are nameless by rule. The surrounding side-panel form's values must never ride along.

## Validation
- **View tests:** replace `test_bookmark_patch_and_inverse_preserve_values_and_retained_help` with fragment assertions:
  - only mounted instances of affected addresses, both suffixes when both are mounted, and companions included;
  - Saved only on the trigger instance;
  - no `inverse` or Undo anywhere;
  - preserved values and retained help in the rendered controls.

  Extend `test_bookmark_failure_preserves_workspace_and_selection` and `test_bookmark_persistence_value_error_remains_server_error` to check the single Not saved status fragment.
- **Jest** (`simplified_bookmark_lifecycle.test.js`, `simplified_inputs.test.js`): keep the creation cases. Rewrite "inline settings payload excludes…" to assert `Object.keys(parameters)` is `["patch", "mounted"]` and that `mounted` lists only non-provisional ids. Remove "saved companion locks remain authoritative…", "a failed help draft survives…" and "bookmark success updates visible membership…", along with the `finishBookmarkRequest` and `bookmarkResponse` helpers.
- **E2E:** in `test_nested_creation_settings_and_failed_help_survive_membership_undo`, remove the Undo steps, invert the help assertion (the saved help replaces the failed draft) and rename it to match. Run `test_failed_bookmark_preserves_the_panel_and_unsaved_value` and `test_inline_sources_creation_requirements_and_delete` unchanged.
- **Commands:** `npm run build:js:dev`, compile the SCSS, `npm run jest`, `poetry run pytest tests --ignore=tests/e2e`, then the full E2E suite.

## Out of scope
Configure-mode selection controls (`configuration.js`), workspace reads and exits (Task 4), and changing what a bookmark can edit.

## Unverified
None. `HX-Trigger` carries the issuing element's id under HTMX 2. Saved bookmarks' `<details>` always have an id (`bookmark.html` line 1).
