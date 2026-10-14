# Task 2 — Verify native export and reconcile the saved-state contract
Written 2026-10-14 against e-footprint-interface `ce018bf3` (with pre-existing unrelated local edits).
Plan: [reads and export](../plan.html#reads-export), [verification](../plan.html#delivery). Task: [overview](../tasks.md#task-2).
Status: under review.

## Start here

- Export capture listener — e-footprint-interface/`theme/static/scripts/simplified_inputs/index.js` — its global-busy early return becomes obsolete; retain the dirty-Configure notice and interception.
- `upload_download_reboot_model_tooltips.html` — `model_builder/templates/model_builder/` — two-model Export is a `<button>` toggle with native `<a>` menu links; one-model Export is directly an `<a>`.
- `test_focused_export_requires_fresh_activation_after_save_and_uses_accepted_state`, `test_blocked_export_never_replays_and_fresh_native_activation_runs_once`, `test_configure_export_blocks_dirty_controls_and_clean_export_stays_open` — `tests/e2e/test_simplified_inputs.py` — current saved-state and busy-export regressions.
- `ModelBuilderPage.download_active_model`, `press_export_control`, `release_export_control` — `tests/e2e/pages/model_builder_page.py` — existing browser helper surfaces.

## Change along the code path

Task 1's editor form now temporarily disables every button during its own request, so a closed two-model menu cannot newly open. Its already-open menu anchors and the one-model direct anchor retain `href`; their endpoint reads accepted repository state at request time. Remove only `index.js`'s `body.dataset.workspaceMutation` short-circuit. Its window-capture handler still checks `workspace.configureForm()?.dataset.dirty` before Bootstrap opens a menu or a native link navigates, then shows the existing notice. No export-specific save trigger, queue, replay or disabled state is needed.

Adapt Jest and Playwright export cases to prove the real control distinctions and accepted-state timing: the two-model toggle is disabled during a delayed field save; a link already available can download the old or just-persisted value, never the unsaved DOM value; settlement schedules no download. Retain clean/dirty Configure, rejection restoration and invalid-draft coverage. Update the old Simplified-input feature docs and export feature docs where they promise one active workspace write or block every export during a write; the new feature [spec](../spec.html#success) is authoritative. Reconcile `architecture/rendering.html`, `workspace.html`, `persistence.html`, `specs/testing.md`, and one consolidated Unreleased changelog entry.

## Earlier tasks

Task 1 removes the shared busy flag and global event bus, installs the editor's native control selector, and updates the general field-save/browser helpers. Do not reintroduce an anchor-stripping guard or use an export click to complete a focused field edit.

## Reuse

- `views_simplified_inputs.py` keeps accepted-state ownership and rejection restoration; existing download endpoints and repository export paths are unchanged.
- The rendered export controls expose `data-workspace-export`, and the `index.js` dirty-Configure listener already intercepts before Bootstrap's document-capture dropdown handler.
- Existing Playwright `page.expect_download()`, `page.route()` and saved JSON assertions cover the repository boundary. `js_tests/simplified_inputs.test.js` mounts Django-rendered fixtures via `js_tests/build_fixtures.py`.

## Invariants and traps

- A native link is intentionally usable during a field save, including a pre-opened two-model menu item. Its file may contain the edit only if persistence wins the timing race; assert saved-state origin, not a fixed old/new outcome.
- A disabled two-model toggle cannot newly open its menu; dirty Configure still blocks a native anchor even when no field save is active. No blocked activation is replayed.
- The former export specification and its review guide contain now-superseded busy/global-lock claims, including their visual flow. Update those claims without changing the prior feature's unrelated accepted-state and dirty-Configure rules.

## Validation

- Focused Jest: `npm run jest -- --runInBand js_tests/simplified_inputs.test.js`; browser: `poetry run pytest tests/e2e/test_simplified_inputs.py -n 4 --base-url http://localhost:8000` after `npm run build:js:dev` and with the local server.
- Complete run gates: `npm run jest`; `poetry run pytest tests --ignore=tests/e2e`; `poetry run pytest tests/e2e -n 4 --base-url http://localhost:8000`. Review documentation links and check `CHANGELOG.md` under `## [Unreleased]`.
- Verify `pyproject.toml`/`poetry.lock` satisfy the repository's PyPI dependency gate before any commit intended for `main`, preserving the unrelated local edits already present.

## Out of scope

No new server endpoint, persistence format, field-save policy, export-specific UI state or global write serialization. Task 1 owns local lifecycle conversion.

## Unverified

The accepted value served by a native download during a delayed save depends on whether persistence has completed. Browser evidence must cover both a held pre-persistence request and a fresh activation after settlement; it must not assume deterministic overlap ordering.
