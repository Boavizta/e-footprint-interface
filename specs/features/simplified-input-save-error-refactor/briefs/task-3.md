# Task 3 — Remove obsolete failed-edit guards and synchronize docs
Written 2026-10-07 against e-footprint-interface `f005dee5`.
Plan: [leave or export](../plan.html#leave-or-export), [delivery](../plan.html#delivery). Task: [Task 3](../tasks.md#task-3--remove-obsolete-failed-edit-guards-and-synchronize-docs).
Status: approved — implementation pending.

## Start here

- `failedExportForm()`, `requireEditRecovery()`, `htmx:confirm`, export click and navigation capture — `theme/static/scripts/simplified_inputs.js` — obsolete failed-draft gates and retained Configure exit logic.
- Destructive confirmations — `theme/static/scripts/model_builder_main.js`, `model_comparison.js` — `discardsSimplifiedEdits` wording to remove while preserving ordinary confirmations.
- `specs/features/simplified-inputs/spec.html` and `plan.html` Decision 08 — old user-facing failed-save promise and design decision.
- `specs/architecture/{runtime-and-recovery,rendering,workspace,persistence,timeseries}.html`, `specs/testing.md`, `CHANGELOG.md` — descriptions that must match the shipped flow.

## Change along the code path

Once Task 2 restores accepted fields, remove the failed-form export check, model replacement/surviving-slot `htmx:confirm` guard, failed-edit view-entry check and recovery notice. Delete the `discardsSimplifiedEdits` branches in both destructive confirmations. Keep `completeFocusedEditForExport()` and `pendingExport`: a focused changed field still saves before download, a failed or invalid save cancels that activation, and a later click exports accepted state. The shared in-flight lock remains. Keep Configure `deferExit()` Save/Discard/Stay and model-removal's ordinary side-panel unsaved-change warning.

Update the original spec's rejected-inline and rejected-timeseries clauses; mark Decision 08 superseded in its original plan and adjust the timeseries text. Align the owning architecture pages, testing guidance and a single Unreleased changelog entry with the delivered behavior. This is the documentation promotion the workspace `AGENTS.md` asks to suggest for a non-trivial pattern; the owning pages already belong to the approved plan, so include them in implementation.

## Earlier tasks

Task 1 made HTTP status the save result and modal OOB processing reliable. Task 2 removed failed-draft state and buttons and returns a repository-backed field on failure. This task removes only guards whose premise was that retained draft; it must not remove Configure or bookmark draft handling.

## Reuse

`js_tests/{simplified_inputs,model_builder_main}.test.js` already contains export and mutation-lock fixtures. `tests/e2e/test_simplified_inputs.py` covers focused export, parked-model failures, Configure exits and replacement; `test_weekly_pattern_builder.py` covers focused timeseries. `specs/architecture/index.html` routes to the five owning detail pages named in the approved plan.

## Invariants and traps

An in-flight mutation still locks actions. The failed focused export click must never download, including native browser validation with no request. Bookmark help and Undo drafts are separate from failed inline values. Remove stale assertions that expect Retry/Discard or parked failed state; replace them with accepted-value and normal-navigation assertions. Rebuild CSS from SCSS; never hand-edit generated `bs_main.css`.

## Validation

Update Jest and Playwright cases listed above, including two-model export and model-removal confirmation, Configure failure, bookmark draft preservation, error modal and panel closure. Run `poetry run pytest tests --ignore=tests/e2e`, `npm run jest`, and `poetry run pytest tests/e2e -n 4 --base-url http://localhost:8000` with the local Django server. Run `npx sass theme/static/scss/main.scss:theme/static/css/bs_main.css --load-path=node_modules/bootstrap/scss` after SCSS changes. Check the PyPI dependency gate before any commit reaches `main` without disturbing the existing local `pyproject.toml`/`poetry.lock` edits.

## Out of scope

Changing library behavior, adding a new feature spec, changing unrelated side-panel dirty-state protection or redesigning export endpoints.

## Unverified

None for the task map. Full browser behavior requires the final local-server E2E gate.
