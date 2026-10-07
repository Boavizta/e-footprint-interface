# Task 3 — Remove obsolete failed-edit guards and synchronize docs

Repository and implementation range: `e-footprint-interface` `8333ab63..606cf186`.

## Review pointers

- `theme/static/scripts/simplified_inputs.js` removes failed-edit export and view-entry gates while retaining focused-save export sequencing, the in-flight mutation lock, and Configure Save/Discard/Stay.
- `theme/static/scripts/model_builder_main.js` and `model_comparison.js` keep ordinary destructive confirmation and side-panel warning copy without failed-inline-edit wording.
- `tests/e2e/test_simplified_inputs.py` uses a real HTTP 422 rejection to verify accepted-field restoration, later accepted-state exports, and navigation/model actions. The timeseries E2E case verifies that a rejected focused Save closes its panel.
- The Configure failure case sends an invalid definition to the real endpoint and verifies its 422 modal OOB preserves the dirty draft and exit guard.

## Open concerns

- The required `poetry run pytest tests --ignore=tests/e2e` gate still fails only at `tests/test_no_dev_dependency.py`: the pre-existing local `pyproject.toml` edit uses `efootprint = {path = "../e-footprint", develop = true}`. The diagnostic run excluding that gate passed all 973 other tests.
- The required `npm run jest` gate still fails only because the pre-existing untracked `tools/vscode-plan-review-links/extension.test.js` imports the unavailable `vscode` module. The product suites passed all 308 tests in the diagnostic run excluding that file.
- The first parallel E2E run had three timing failures in `tests/e2e/test_forms.py::TestUnsavedChangesWarning::test_pending_request_preserves_hx_vals`, `tests/e2e/objects/test_edge_device_groups.py::TestEdgeDeviceGroups::test_group_edit_panel_links_and_unlinks_members_live`, and `tests/e2e/objects/test_video_external_api_objects.py::TestVideoExternalAPIObjects::test_ecologits_video_full_workflow`. They passed focused sequential runs, and the corrected full E2E rerun passed all 152 tests; retain the intermittent timing signal.
