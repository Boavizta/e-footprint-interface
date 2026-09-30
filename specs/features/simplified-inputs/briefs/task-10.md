# Task 10 — Complete timeseries, export and release checks

Written 2026-09-30 against e-footprint `96ea0d39` and e-footprint-interface `fe6c04e5`.
Plan: [timeseries](../plan.html#timeseries), [exports](../plan.html#exports), [verification](../plan.html#verification). Task: [overview](../tasks.md#task-10). Status: approved.
Implementation: standard — use the existing timeseries registry/panel and Task 6/9 save state in current export controls, then run integrated gates.

## Start here

- [`timeseries_builder_registry.py`](../../../../model_builder/adapters/forms/timeseries_builder_registry.py), [`views_timeseries_preview.py`](../../../../model_builder/adapters/views/views_timeseries_preview.py): compatible builder strategies and stateless draft preview.
- [`side_panel_utils.js`](../../../../theme/static/scripts/side_panel_utils.js): draft warning/close behavior; [`test_timeseries.py`](../../../../tests/e2e/test_timeseries.py): current editor/preview behavior.
- [`views.download_json()`/`download_workspace()`](../../../../model_builder/adapters/views/views.py), [`upload_download_reboot_model_tooltips.html`](../../../../model_builder/templates/model_builder/upload_download_reboot_model_tooltips.html): normal export entry points.

## Change along the code path

Add a field-only timeseries side panel with existing strategy selector, builder partials, parser and stateless preview. Load it when Edit timeseries is clicked beside the string preview. Keep the visual chart left of the panel at tablet/desktop widths and in form flow on phones. Save through Task 5's selected-input use case; Cancel discards; failure keeps panel and draft for retry. Model switching uses the existing side-panel discard warning and closes the editor when continued. Extend export handling so a focused simplified field saves before download, all export links/menus wait for relevant in-flight saves, and failed autosaves block export until corrected/retried or explicitly discarded. Configure's Task 7 exit guard applies to export; ordinary Modeling panel export behavior stays as it is. Finish critical integrated flows, documentation, changelogs and release gates.

## Earlier tasks

Tasks 1–9 provide renamed examples, corrected library validation, configuration, atomic edit, guard, shared view, bookmarks and simple autosave/totals.

## Reuse

Use current timeseries registry/preview, `side_panel_utils.js` discard warning, standard single-model/workspace export endpoints and `tests/e2e/pages/` page-object conventions. Do not add another download format, saved timeseries draft store or background mutation queue.

## Invariants and traps

Only one timeseries editor/preview is active. A modal error is HTTP 200; do not close the panel or continue export on it. An unfinished timeseries panel exports the last saved value, like ordinary Modeling panels. The last focused simple field must commit before export; export of both models waits for saves in the requested models. Opening Results/Sources and switching models also honor Configure's Save/Discard/Stay guard. Reconcile complete/failed saves with UI status before treating exported data as current.

## Validation

Run focused `poetry run pytest tests/e2e/test_simplified_inputs.py tests/e2e/test_timeseries.py --base-url http://localhost:8000` against a local server, plus simplified-input/export Jest tests. Cover strategy switch and preview, Save/Cancel, rejected save retry, model-switch discard, final focused-field download, failed-save export stop, two-model export and JSON reopen. Then run full interface `poetry run pytest tests --ignore=tests/e2e`, `poetry run pytest tests/e2e -n 4 --base-url http://localhost:8000` and `npm run jest`; run full library `poetry run pytest`, `poetry run mkdocs build --strict` and installed-resource checks. Confirm the interface dependency in `pyproject.toml` and `poetry.lock` points to PyPI before any merge to main; do not overwrite the pre-existing local edits during task preparation. Add consolidated Unreleased changelog entries and update owning architecture, design and relevant AGENTS/CLAUDE pointers for the new patterns.

## Out of scope

No hosted sharing, alternative file format, queued autosave or change to ordinary Modeling unsaved-export behavior.

## Unverified

Production-sized render measurements and local E2E environment are implementation checks; no benchmark or product gate result is claimed by this brief.
