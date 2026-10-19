# Task 4 — Reads, exits, Results close and close-out docs
Repositories and implementation ranges: `e-footprint-interface` `0c683307..2ea58d03`.

## Review pointers
- `hx-sync="this:replace"` on the slot is inherited by the Configure form, which declares no `hx-sync`. Its Save therefore shares the slot's replace queue with reads: a Discard read issued during a Save aborts the Save's XHR, and the server may still commit it. Field editors keep their own `this:drop`. `workspace.html` states the inheritance.
- The workspace API now returns only `activeWorkspace`, `configureForm`, `initialize` and `registerWorkspace`. `setBaseView` and `loadView` are private.
- `hidePanelResult()` no longer sets `display: none`, so the `htmx:afterSettle` layout hook drops its display check.
- `test_field_save_disables_both_resident_workspaces_and_restores_controls` now enters Simplified inputs in model 0 after Duplicate, as the accepted rebuild rule requires.
- The double-click E2E holds both Configure reads, renders the second, types a draft and then fulfills the aborted first read. Playwright accepts that fulfillment without error, and the draft survives.
- Settle-class waits in `side_panel_page.py`, `model_builder_page.py`, `test_source_metadata.py` and `test_simplified_inputs.py` now use `wait_for_htmx_idle()`. `testing.md` was reconciled, including a stale "navigation can still cancel" read sentence.
- The changelog's existing module-split entry no longer lists a field-edit module.

## Open concerns
- `add_model_by_duplication()` still waits 20 ms for a settle phase that no longer exists. It is harmless and was left unchanged.
