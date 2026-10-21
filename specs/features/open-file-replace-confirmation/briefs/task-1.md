# Task 1 — Confirm before "Open a file" replaces a modeling
Written 2026-10-21 against e-footprint-interface `dev` @ `9dc54426`.
Plan: [1.1 Press Open](../plan.html#press-open), [1.2 E2E helper](../plan.html#tests),
[Delivery and verification](../plan.html#delivery). Task: [tasks.md, Task 1](../tasks.md#task-1--confirm-before-open-a-file-replaces-a-modeling).
Status: approved.

## Start here
- `open_import_json_panel()` — `model_builder/adapters/views/views.py` — renders the panel; add the message to its context.
- `#sidePanelForm` — `model_builder/templates/model_builder/side_panels/import_model.html` — the form that POSTs to `upload-json`; add the attribute.
- body-level `htmx:confirm` listener under "Conditional confirmation for destructive model-replacing actions" — `theme/static/scripts/model_builder_main.js` — the guard being reused; update its comment only.
- `ModelBuilderPage.import_json_file()` — `tests/e2e/pages/model_builder_page.py` — shared upload helper that must accept the new dialog.

## Change along the code path
1. GET `/model_builder/open-import-json-panel/` → `open_import_json_panel()` computes
   `len(SessionWorkspaceRepository(request.session).list_slots()) > 1` and passes `replace_confirmation`
   (exact strings in [plan 1.1](../plan.html#press-open)). `SessionWorkspaceRepository` is already imported in `views.py`.
2. `import_model.html` form gains `data-confirm-when-model-not-empty="{{ replace_confirmation }}"`.
3. Pressing Open: htmx fires `htmx:confirm` on the form → existing listener finds the attribute, skips when
   no `.model-builder-card` exists anywhere in the page (both slot canvases are rendered, the inactive one `d-none`),
   otherwise `window.confirm(message)` and `issueRequest(true)` on OK. `upload_json()` is unchanged.
4. Extend the listener's leading comment ("toolbar reboot, picker cards") to name the "Open a file" form.
5. `CHANGELOG.md`: one line under `## [Unreleased]` → `### Fixed` (section already exists).

## Earlier tasks
None.

## Reuse
- The existing `data-confirm-when-model-not-empty` listener; no new JS, no Jest change.
- Single-session wording copies the picker's string in `onboarding/template_picker.html` verbatim.
- E2E dialog-capture pattern: `test_reboot_confirms_after_adding_to_initially_empty_model` in `tests/e2e/test_toolbar.py`.
- Integration two-slot setup: `_seed_active_slot()` + `client.post("/model_builder/add-model/", {"source": "blank"})`,
  as in `test_single_model_file_via_open_file_in_two_model_session_replaces_active_slot` (`tests/integration/test_workspace_file.py`).

## Invariants and traps
- Playwright auto-dismisses dialogs. Without the helper change, every `import_json_file()` call over a
  non-empty modeling cancels and its `expect_response("upload-json")` times out. Callers: `conftest.py`,
  `test_card_order_persistence.py`, `test_data_privacy.py`, `test_simplified_inputs.py` (×2),
  `test_source_metadata.py`, `test_toolbar.py` (×2), `test_weekly_pattern_builder.py`. None uses the return
  value (today `self`), so returning the message list is safe.
- Register the helper's handler with `page.on` and remove it in `finally` after the response
  ([plan 1.2](../plan.html#tests)); a `page.once` would linger on empty-model imports and accept an unrelated later dialog.
- The panel is re-fetched on every open, and add-model/remove-model discard an open panel, so the
  server-rendered wording cannot go stale relative to the slot count.
- Side-panel guards in `side_panel_utils.js` do not apply: `upload-json` targets `#main-content-block` and is
  not in `PANEL_DISCARDING_PATHS`. Do not add it there.
- Do not touch `add_model_import.html` ("Import a modeling to compare" adds, never replaces).

## Validation
- Integration (`tests/integration/test_workspace_file.py`): GET the panel in a one-slot session → HTML contains
  "This will replace your current modeling. Continue?"; in a two-slot session → contains the comparison text.
- E2E (`tests/e2e/test_toolbar.py`):
  - `test_import_json_replaces_existing_model`: assert the returned messages equal `["This will replace your current modeling. Continue?"]`.
  - `test_import_json_into_empty_model_adds_objects`: assert returned messages are empty.
  - New test: dismiss the dialog over `minimal_complete_model_builder`; assert no `upload-json` request was sent
    (record requests via `page.on("request")`), the original cards remain, and the panel is still open.
- Commands: `poetry run pytest tests --ignore=tests/e2e`; with the local server running,
  `poetry run pytest tests/e2e -n 4` (full run, because the helper is shared). `npm run jest` per constitution, expected unchanged.

## Out of scope
Undo; styled modal; file-content-dependent wording; any change to `upload_json()` detection or restore.

## Unverified
None.
