# Open a file: confirm before replacing — tasks
Spec: [spec.html](spec.html) · Plan: [plan.html](plan.html)
Status: approved

## Implementation runs
| Run | Delivered milestone | Tasks in execution order | Prerequisites |
|---|---|---|---|
| A | "Open a file" asks before replacing a modeling with content | [1](#task-1--confirm-before-open-a-file-replaces-a-modeling) | None |

## Overview
| Task | Delivered behavior | Plan section | Repository | Implementation |
|---|---|---|---|---|
| 1 | Session-aware confirmation on the panel's Open; E2E helper accepts it | [1.1](plan.html#press-open), [1.2](plan.html#tests) | e-footprint-interface | easy |

## Task 1 — Confirm before "Open a file" replaces a modeling
Goal: pressing Open in the "Open a file" panel asks first when any modeling has content, with the
single-session or comparison-session wording; Cancel uploads nothing.
Status: approved
Brief: [briefs/task-1.md](briefs/task-1.md)
Repository: e-footprint-interface
Files touched: `model_builder/adapters/views/views.py`,
`model_builder/templates/model_builder/side_panels/import_model.html`,
`theme/static/scripts/model_builder_main.js` (comment only), `tests/e2e/pages/model_builder_page.py`,
`tests/e2e/test_toolbar.py`, `tests/integration/test_workspace_file.py`, `CHANGELOG.md`.
Tests: integration test for the two wordings; E2E assertions for prompt over content, no prompt on
an empty modeling, and Cancel keeping the modeling and panel; full E2E run for the other helper callers.
Acceptance: every row of the [plan's verification map](plan.html#delivery) holds; existing
confirmations (picker, Reset, ✕ remove) unchanged; `CHANGELOG.md` has one `### Fixed` line.
Depends on: none.
Implementation: easy — one attribute and one view conditional reusing the existing body-level
confirm listener; the only test-side change is a bounded dialog handler in one shared helper.
