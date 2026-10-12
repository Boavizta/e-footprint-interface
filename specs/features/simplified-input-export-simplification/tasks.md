# Simplified-input export simplification — tasks

Spec: [spec.html](spec.html) · Plan: [plan.html](plan.html)
Status: Run A delivered and reviewed; outstanding validation prerequisites below · Authorized by `/feature-implement` on 2026-10-12.

## Implementation runs

| Run | Delivered milestone | Tasks in execution order | Prerequisites |
|---|---|---|---|
| A | Saved-state export with fresh activation after a blocked gesture, verified in the browser and documented | [1](#task-1--replace-export-continuation-with-saved-state-admission) → [2](#task-2--verify-native-activation-and-downloaded-state) → [3](#task-3--reconcile-export-documentation) | Implementation authorized; current shared mutation lock. Implement before `simple-workspace-mutation-gate`; its redesign is not a dependency. |

## Overview

| Task | Delivered behavior | Plan section | Repository | Implementation |
|---|---|---|---|---|
| [1](#task-1--replace-export-continuation-with-saved-state-admission) | Ordinary inline autosave; no export replay; dirty Configure blocks with existing status feedback; clean Configure exports in place | [Activation](plan.html#activation), [Configure](plan.html#configure) | e-footprint-interface | standard — integrate existing save, capture-listener and Configure-exit mechanisms with their behavioral tests |
| [2](#task-2--verify-native-activation-and-downloaded-state) | Browser regressions prove busy admission, fresh mouse/keyboard activation and accepted file contents | [Delivery](plan.html#delivery) | e-footprint-interface | standard — control browser gestures and response settlement using established Playwright fixtures and page objects |
| [3](#task-3--reconcile-export-documentation) | Architecture, testing guidance and older feature artifacts describe the delivered export policy | [Delivery](plan.html#delivery) | e-footprint-interface | easy — bounded replacement of superseded claims using Task 2's verified behavior |

## Task 1 — Replace export continuation with saved-state admission

Goal: Remove focused-edit and Configure export continuations while preserving ordinary saves and other Configure exits.

Status: complete

Brief: [briefs/task-1.md](briefs/task-1.md)

Repository: `e-footprint-interface` only.

Files touched: `theme/static/scripts/simplified_inputs/{index,field_edits,workspace}.js`; `js_tests/simplified_inputs.test.js`; `js_tests/build_fixtures.py` if Configure needs named one/two-model toolbar fixtures. Retain existing `js_tests/model_builder_main.test.js` guard coverage; extend only for uncovered behavior.

Tests: Replace export-continuation assertions with ordinary focusout/Enter/provenance save and no-replay assertions; cover clean/dirty Configure, all marked export controls, notice replacement, failed save and explicit Save/Discard resolution. Load the real shared guard for busy-admission assertions. Run targeted Jest, then all Jest.

Acceptance:

- No focused-export method, pending export, export callback, replayed download or export-specific mouse-press interception remains.
- Export itself neither validates nor submits an inline draft. Ordinary autosave, accepted-field status, server-error restoration and timeseries-panel closure remain intact.
- Busy export remains suppressed by the current guard, including menu activation and native link destinations; settlement never opens a menu or downloads.
- Dirty Configure suppresses every marked export control before Bootstrap capture and displays one status notice: “Save or discard Configure changes before exporting.” It initiates no save, read or exit dialog.
- Clean Configure exports directly and stays open. Export bypasses the generic exit interceptor before read cancellation; other Save / Discard / Stay flows retain their internal continuations.
- Saving or discarding removes the notice through the existing workspace replacement; failed Configure save retains its dirty draft and export blocking.

Depends on: none.

Implementation: standard — the design and ownership are established; integrating existing event listeners and meaningful guard/Configure tests requires ordinary implementation judgment.

## Task 2 — Verify native activation and downloaded state

Goal: Prove the Task 1 policy through real focus movement, Bootstrap menus, HTMX responses and downloaded JSON.

Status: complete; publishable-dependency gate remains outstanding below

Brief: [briefs/task-2.md](briefs/task-2.md)

Repository: `e-footprint-interface` only.

Files touched: `tests/e2e/pages/model_builder_page.py`; `tests/e2e/test_simplified_inputs.py`. Rebuild ignored `theme/static/bundles/` assets with `npm run build:js:dev`.

Tests: Adapt the focused-export and one/two-model activation workflows; add clean/dirty Configure export coverage and adapt the Configure-failure export assertion. Keep parked-model rejection and unfinished-timeseries export coverage. Run focused E2E, then the full constitutional Python/E2E and Jest gates against rebuilt assets.

Acceptance:

- Delayed numeric and provenance saves block the first gesture; releasing it and settling the response cause no download/menu opening. A separate fresh activation exports the saved value/comment exactly once.
- One/two-model controls cover mouse activation and keyboard admission, including Tab then Enter, Space on the menu button and an abandoned mouse press. Abandoning a press may start ordinary blur autosave; it must never export.
- Browser-invalid input issues no save; idle export can contain the previous accepted value without export-specific validation. Do not require the first mouse gesture to download when native validity restores focus.
- Server rejection restores accepted fields and shows the existing modal; after dismissal, fresh activation exports accepted data.
- Dirty Configure blocks menu opening and both download choices, retains its screen and one notice, and starts no exit dialog. Explicit Save or Cancel → Discard never exports automatically; failed Save remains blocked. Clean Configure exports without leaving.
- Whole-workspace files retain both accepted models after a parked-model rejection. The later model's ordinary save explicitly settles before ready-download helpers run.
- Unfinished Modeling and timeseries panels retain their saved-state export behavior; required suites pass or unavailable checks/failures remain explicit.

Depends on: Task 1.

Implementation: standard — deterministic response holding, physical gestures and file assertions use existing mechanisms but require care around focus, disabled controls and swapped locators.

## Task 3 — Reconcile export documentation

Goal: Replace superseded export promises with the verified saved-state policy and keep the original Simplified-input review guide coherent.

Status: implementation complete; rendered mockup verification unavailable below

Brief: [briefs/task-3.md](briefs/task-3.md)

Repository: `e-footprint-interface` only.

Files touched: `specs/architecture/{persistence,workspace}.html`; `specs/testing.md`; `specs/features/simplified-inputs/{spec,plan}.html`, including the spec's embedded mockup export policy. `CHANGELOG.md` receives one consolidated entry at feature close-out. Suggest changing `AGENTS.md`'s “Save-aware export” pointer label to “Saved-state export”; flag the corresponding `CLAUDE.md` pointer if applicable.

Tests: Audit affected prose, verification text, mockup behavior and links against Tasks 1–2; inspect changed HTML in the browser. No new product tests for prose-only changes. If executable mockup behavior changes, verify its ordinary export and Configure flows in the rendered mockup.

Acceptance:

- Current guidance no longer promises forced focused completion, automatic replay, export-specific invalid-edit cancellation or Configure export deferral.
- Document ordinary blur autosave, busy suppression, fresh activation, accepted-state export after rejection/invalidity, dirty-Configure feedback and clean-Configure export in place.
- Preserve the shared write guard and other Configure exit protections; distinguish the later mutation-gate redesign from current behavior.
- Older Simplified-input prose, linked verification descriptions and mockup agree with this follow-up; record the delivered behavior under `## [Unreleased]` once at run close-out.

Depends on: Tasks 1 and 2.

Implementation: easy — explicit replacement policy and verified predecessors leave a bounded documentation/mockup alignment pass.

## Gates and prerequisites

- **Implementation authorized:** `/feature-implement simplified-input-export-simplification` authorizes Run A and its existing spec, plan and task breakdown.
- **Local verification environment resolved:** this interface checkout runs at `http://localhost:8000` with rebuilt bundles, its configured local database/cache and Playwright browser.
- **Outstanding full-Python gate:** `tests/test_no_dev_dependency.py::TestNoDevDependency::test_no_active_develop_true_in_pyproject` fails because the pre-existing dependency points to editable `../e-footprint`. Preserve the owner’s dependency edits; restore PyPI deliberately before merge and rerun this guard. Other full-Python checks have no outstanding failure. No full-E2E or Jest gate remains outstanding. No library API or Django schema change is planned, so no migration or library gate is triggered.
- **Blocks merge to main:** restore a publishable PyPI dependency deliberately, preserving the pre-existing `pyproject.toml`/`poetry.lock` edits until their owner resolves them. Current checkout uses editable `../e-footprint`; do not reset those files as part of this feature. The middleware edit is also pre-existing and outside scope.
- **Ordering:** complete this run against the current shared lock before implementing `simple-workspace-mutation-gate`. If that lock changes first, re-ground the guard-dependent briefs and checks before implementation.
- **Unavailable documentation verification:** browser security policy rejected the local `file://` mockup URL and explicitly prohibited alternate routes or workarounds. HTML/script syntax, links and static behavior review are complete; rendered clean/dirty Configure and save/export mockup interactions remain unverified. This limitation does not apply to the actual application’s completed E2E verification.
- No deployment-only prerequisite is introduced. No material departure from the approved product plan was required.
