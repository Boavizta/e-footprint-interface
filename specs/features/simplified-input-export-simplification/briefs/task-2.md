# Task 2 — Verify native activation and downloaded state

Written 2026-10-12 against `e-footprint-interface` commit `07fac466497e63bb8b54ee54183fc91f9665939f` and its current working-tree plan.
Plan: [Delivery and verification](../plan.html#delivery).
Task: [Task 2](../tasks.md#task-2--verify-native-activation-and-downloaded-state).
Status: under review.

## Start here

- `press_export_control`, `release_export_control`, `download_active_model`, `download_workspace` — `tests/e2e/pages/model_builder_page.py`: physical gesture helpers versus already-ready download helpers.
- `test_focused_edit_export_waits_for_save_and_rejected_or_invalid_edit_cancels_download`, `test_export_waits_for_activation_and_runs_once` — `tests/e2e/test_simplified_inputs.py`: replace automatic completion assumptions.
- `TestSimplifiedInputs.test_configure_save_failure_retains_the_draft_and_exit_guard`: replace its export-triggered exit-dialog expectation while retaining other navigation protection.
- `test_workspace_export_uses_accepted_state_after_other_model_rejection`, `test_focused_hourly_panel_save_cancel_failure_and_mobile_preview`: preserve file-content and unfinished-timeseries coverage.

## Change along the code path

Build current client assets, then drive ordinary edits and marked toolbar controls through the page object. Hold matching edit-save responses with Playwright routing to make the busy interval deterministic. Begin the physical mouse gesture, confirm ordinary blur started one save and shared busy state, release or abandon it, then release the response and wait for accepted-field settlement/unlock. Assert no download/menu opening before a separate fresh activation. Read downloaded JSON to verify scalar `value`, provenance `comment`, and each workspace `models[]` accepted state.

Add page-object helpers for keyboard admission (Tab out of the changed editor, then Enter; Space on the two-model menu button) and blocked gestures where existing methods are insufficient. Keep ready-download helpers free of implicit saves/retries. Test clean/dirty Configure with one/two models and both download choices: blocking notice, retained Configure, no dialog/read/save/download; Save and return or Cancel → Discard resolves the draft without automatic action. Failed Configure Save must keep export blocked; a clean Configure export stays on Configure.

## Earlier tasks

Task 1 supplies the simplified constructor/API, no stored export intent, dirty-Configure window-capture admission and the generic exit exclusion. It retains current shared locking and all non-export continuations. This task consumes those behaviors rather than designing a new guard.

## Reuse

`minimal_complete_model_builder`, `open_configure`, `field`, `reject_simplified_edit`, existing Configure rejection routing, `builder.add_model_by_duplication()`/`switch_to_model()`, `tmp_path` JSON assertions. Reuse `click_and_wait_for_htmx` and `wait_for_htmx_idle` from `tests/e2e/utils.py` for ordinary issued requests; blocked controls should issue none. `tests/e2e/conftest.py` suppresses first-run onboarding and defaults to local port 8000. Read `tests/e2e/AGENTS.md` and `specs/testing.md` before editing.

## Invariants and traps

Playwright `locator.click()` may wait for a disabled button to re-enable and then activate it, hiding a blocked gesture. Use physical press/release and explicit keyboard sequences for admission; never add helper retries. Abandoned mouse presses can now blur/save and must not download. Browser-invalid blur may restore focus and consume the first gesture; assert no save and accepted-state export on a fresh idle activation rather than promising first-click download. Rejection replaces editors: reacquire locators and wait for the modal plus accepted fields, then dismiss the error before exporting. Make the second model's ordinary save settle explicitly before its ready export helper. Preserve unfinished Modeling/timeseries drafts and other Configure exits.

## Validation

From the interface root, `npm run build:js:dev`; run a local `poetry run python manage.py runserver` with configured local database/cache and installed browser. Confirm the server uses this checkout and rebuilt assets, not another worktree. Then `poetry run pytest tests/e2e/test_simplified_inputs.py --base-url http://localhost:8000`.

Cover delayed numeric/provenance saves; rejection/invalidity; abandoned mouse press; mouse, Tab/Enter and menu Space; clean/dirty Configure and explicit Save/Discard; active/workspace downloaded values; parked rejection; unfinished timeseries and Modeling exports. Keep tests distinct and use existing related suites for established Modeling behavior. Assert no save/read/download during dirty blocking and no replay after settlement without arbitrary sleep-based readiness.

Run final gates once the code is final: `poetry run pytest tests --ignore=tests/e2e`, `poetry run pytest tests/e2e -n 4 --base-url http://localhost:8000`, `npm run jest`. Preserve and report any missing environment check or failure, including the current local editable-dependency guard; resolve deliberately before main. Build outputs are ignored, not source files to stage. Do not start parallel stateful suites against shared mutable application state.

## Out of scope

Production validation/deployment, persistence changes, new browser state, mutation-gate redesign, silent retries/reloads or alterations to pre-existing middleware/dependency edits.

## Unverified

Application tests have not run during task preparation. Availability of the local server/cache/database/browser is an implementation verification prerequisite, not evidence of a plan gap.
