# Simplified-input save lock — tasks
Spec: [spec.html](spec.html) · Plan: [plan.html](plan.html)
Status: complete

## Implementation runs

| Run | Delivered milestone | Tasks in execution order | Prerequisites |
|---|---|---|---|
| A | Simplified field saves use a scoped native lock; independent actions, export and documentation match the approved spec | [1](#task-1), [2](#task-2) | Approved tasks; local frontend build and browser test environment for verification |

## Overview

| Task | Delivered behavior | Plan section | Repository | Implementation |
|---|---|---|---|---|
| [1](#task-1) | Field saves lock native controls and settle locally; other actions no longer depend on the workspace guard | [Save](plan.html#save), [cleanup](plan.html#cleanup) | e-footprint-interface | hard — coordinating HTMX completion, OOB replacements and several former event consumers remains technically coupled |
| [2](#task-2) | Native exports follow saved-state rules; regression coverage and documentation reflect the new boundary | [Reads and export](plan.html#reads-export), [delivery](plan.html#delivery) | e-footprint-interface | standard — known export controls and tests need ordinary integration and documentation work |

<a id="task-1"></a>
## Task 1 — Scope the save lock and retire the shared mutation lifecycle

Goal: A valid Simplified-input value or provenance save submits the full value, disables buttons and both resident Simplified-input workspaces for its own request, then restores real prerequisite-disabled states and local save feedback on success or failure. Other actions keep their own completion behavior without a global workspace mutation bus.

Status: complete

Brief: [briefs/task-1.md](briefs/task-1.md)

Repository: e-footprint-interface

Files touched: `model_builder/templates/model_builder/simplified_inputs/editor.html`; `theme/static/scripts/model_builder_main.js`, `simplified_inputs/field_edits.js`, `simplified_inputs/bookmarks.js`, `simplified_inputs/workspace.js`, `source_metadata.js`, `sankey.js`, `hammer_utils.js`; `js_tests/model_builder_main.test.js`, `js_tests/simplified_inputs.test.js`, `js_tests/simplified_bookmark_lifecycle.test.js`, `tests/e2e/test_simplified_inputs.py`, `tests/e2e/test_model_comparison.py`, `tests/e2e/utils.py`, and related page-object helpers if their old lock probes become unused.

Tests: Adapt Jest tests for the native disabled selector, prerequisite restoration, field status and accepted snapshots, Configure Save/Discard/Stay, bookmark status, card order and Results cleanup. In Playwright, delay a field save to assert payload, both workspaces, no second field request, outcome restoration and ordinary independent-action behavior; replace global-lock assertions in Simplified-input and comparison tests. Run focused Jest/E2E checks, then the run gates.

Acceptance: No `workspace-mutation:*` listeners or emitters and no producer of `body.dataset.workspaceMutation` remain; Task 2 removes the export listener's now-inert busy check. A valid field edit sends once; temporary native disabling covers the intended controls and releases after success, rejected OOB response or transport error. An unchanged blur does not resave; server rejection restores accepted controls and shows Not saved. Configure continuations, bookmarks, timeseries panel closure, card-order fetch and Sankey cleanup retain their own request behavior.

Depends on: none.
Implementation: hard — the shared guard currently coordinates `htmx:afterRequest` with `htmx:afterSettle` for OOB field replacement and also drives Configure, bookmarks and Results. The plan fixes ownership, but transferring these timing paths without losing accepted snapshots or exit continuations still needs careful event reasoning.

<a id="task-2"></a>
## Task 2 — Verify native export and reconcile the saved-state contract

Goal: Export follows the approved field-save rule: the two-model toggle is disabled during a field save, while native links already available can download the repository's current saved state; dirty Configure still blocks export in place. Published guidance no longer promises a broad workspace lock.

Status: complete

Brief: [briefs/task-2.md](briefs/task-2.md)

Repository: e-footprint-interface

Files touched: `theme/static/scripts/simplified_inputs/index.js`; export cases in `js_tests/simplified_inputs.test.js` and `tests/e2e/test_simplified_inputs.py`, plus `tests/e2e/pages/model_builder_page.py` only if an export helper needs adjustment; `specs/architecture/rendering.html`, `workspace.html`, `persistence.html`, `specs/testing.md`, `specs/features/simplified-inputs/spec.html` and `plan.html`, `specs/features/simplified-input-export-simplification/spec.html` and `plan.html`, and `CHANGELOG.md`.

Tests: Adapt saved-state export Jest and Playwright cases for one-model direct links, a pre-opened two-model menu, a disabled toggle, no deferred replay, dirty/clean Configure and rejected or invalid field values. Run `npm run build:js:dev`, `npm run jest`, `poetry run pytest tests --ignore=tests/e2e`, and `poetry run pytest tests/e2e -n 4` with the required local server.

Acceptance: A delayed field save cannot newly open the two-model menu; links remain native and never read unsaved browser fields. Export does not force, queue or resume a save. Dirty Configure blocks with its existing notice, clean Configure exports in place. Architecture, testing, older feature documents and the Unreleased changelog describe the replacement behavior consistently.

Depends on: Task 1.
Implementation: standard — the controls, saved-state endpoint and dirty-Configure listener already exist; the remaining work is to align integration tests and documentation with their new admission rule.

## Gates and prerequisites

- Implementation requires a rebuilt Simplified-input bundle before browser checks: `npm run build:js:dev` in e-footprint-interface. Generated assets must follow repository conventions.
- Browser checks require the local Django server and the Playwright environment described in [testing.md](../../testing.md); use no production services. The full Jest, Python unit/integration and E2E gates apply to the completed run.
