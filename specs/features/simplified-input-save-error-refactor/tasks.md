# Simplified input save errors — tasks
Spec: [original Simplified-input spec](../simplified-inputs/spec.html) · Plan: [approved refactor plan](plan.html)
Status: in progress — Task 1 implemented and reviewed; full workspace gates pending. This refactor uses the existing feature spec; the plan intentionally creates no new `spec.html`.

## Implementation runs

| Run | Delivered milestone | Tasks in execution order | Prerequisites |
|---|---|---|---|
| A — save-error refactor | HTTP errors open their modal, rejected inline and timeseries edits show accepted state, obsolete recovery gates are removed, and documentation matches | [1](#task-1--return-real-error-statuses-and-process-modal-oob), [2](#task-2--restore-accepted-simplified-fields-on-rejected-saves), [3](#task-3--remove-obsolete-failed-edit-guards-and-synchronize-docs) | Approved plan; interface development dependencies and local E2E server for the final gate |

## Overview

| Task | Delivered behavior | Plan section | Repository | Implementation |
|---|---|---|---|---|
| [1](#task-1--return-real-error-statuses-and-process-modal-oob) | 422 validation and 500 unexpected errors keep OOB modals visible and report failure by HTTP status | [1.1](plan.html#modal-response) | e-footprint-interface | standard |
| [2](#task-2--restore-accepted-simplified-fields-on-rejected-saves) | Rejected inline and timeseries saves restore the repository field; failed timeseries Save closes its panel | [1.2](plan.html#inline-edit), [1.4](plan.html#other-saves) | e-footprint-interface | standard |
| [3](#task-3--remove-obsolete-failed-edit-guards-and-synchronize-docs) | Export and navigation no longer require failed-edit recovery; docs and release note describe the new behavior | [1.3](plan.html#leave-or-export), [delivery](plan.html#delivery) | e-footprint-interface | easy |

## Task 1 — Return real error statuses and process modal OOB

Goal: Recognized save validation returns HTTP 422; unclassified exceptions return HTTP 500. Both still display the existing modal OOB, leave the main target intact, and settle the workspace mutation as failed.
Status: implemented and reviewed — full workspace gates pending
Brief: [briefs/task-1.md](briefs/task-1.md)
Repository: e-footprint-interface only.
Files touched: `model_builder/adapters/views/exception_handling.py`, `views_addition.py`, `views_edition.py`, `views_simplified_inputs.py`; `theme/static/scripts/modal_utils.js`, `model_builder_main.js`, `simplified_inputs.js`; focused view, integration, middleware and Jest tests.
Tests: Assert 422 on identified parsing/domain rejections, including `WeeklyPatternValidationError`; 500 on generic or persistence failures; modal OOB and `HX-Reswap: none` on both; no whole-builder replacement; status-driven mutation and bookmark failure.
Acceptance: No save-outcome check reads `openModalDialog`; non-2xx modal bodies are processed OOB; successful responses remain 200 and retain existing panel behavior.
Depends on: none.
Implementation: standard — Validation must be identified at its source while the shared decorator remains a 500 fallback, then HTMX settlement must honor the new status without a target swap.

## Task 2 — Restore accepted Simplified fields on rejected saves

Goal: On a rejected inline value or provenance save, render the selected field from a fresh active repository read; show `Not saved` on the replacement without preserving a retryable draft. A rejected timeseries Save closes its panel after the accepted field is restored.
Status: approved — implementation pending
Brief: [briefs/task-2.md](briefs/task-2.md)
Repository: e-footprint-interface only.
Files touched: `model_builder/adapters/views/views_simplified_inputs.py`, `model_builder/adapters/presenters/simplified_inputs.py`, `model_builder/templates/model_builder/simplified_inputs/{editor,timeseries_panel}.html`, `theme/static/scripts/simplified_inputs.js`, `theme/static/scss/_simplified_inputs.scss`, generated `theme/static/css/bs_main.css` and `.map`; targeted Python, Jest and E2E tests.
Tests: Rejections before persistence restore old value and metadata; a failure after persistence restores the newly stored field; quick total and Results stay at accepted content; invalid browser input issues no save or download; failed timeseries Save closes the panel and discards its draft.
Acceptance: The error response carries one accepted-field OOB fragment plus the existing modal, without a full workspace or total re-render. Retry/Discard and `data-save-failed` are gone; successful save and focused export sequencing remain.
Depends on: Task 1's 422/500 modal contract and status-driven mutation settlement.
Implementation: standard — The endpoint must distinguish request-local mutations from the repository's accepted state across failures before, during and after persistence, then coordinate OOB replacement with save completion.

## Task 3 — Remove obsolete failed-edit guards and synchronize docs

Goal: Remove navigation, model-replacement and export recovery checks that existed for retained failed inline drafts. Preserve Configure's explicit Save/Discard/Stay guard, ordinary side-panel protection and save-aware focused export.
Status: approved — implementation pending
Brief: [briefs/task-3.md](briefs/task-3.md)
Repository: e-footprint-interface only.
Files touched: `theme/static/scripts/{simplified_inputs,model_builder_main,model_comparison}.js`; `js_tests/{simplified_inputs,model_builder_main}.test.js`; `tests/e2e/{test_simplified_inputs,test_weekly_pattern_builder}.py`; `specs/features/simplified-inputs/{spec,plan}.html`; owning architecture pages (`runtime-and-recovery`, `rendering`, `workspace`, `persistence`, `timeseries`), `specs/testing.md`, `CHANGELOG.md`.
Tests: Failed focused export cancels that click; later export uses accepted state. Model/view/shell actions proceed after a failed inline save. Failed Configure Save retains its draft and exit guard; bookmark help/Undo drafts and ordinary side-panel confirmation remain. Run the complete required gates.
Acceptance: No failed-inline-edit recovery prompts or confirmation copy remain. The original spec and Decision 08 explicitly reflect the shipped behavior; architecture/testing docs and the Unreleased changelog agree.
Depends on: Tasks 1–2.
Implementation: easy — Once Task 2 removes retained failed-edit state, this is a bounded deletion and documentation update with explicit regression cases; no new state mechanism remains to design.

## Gates and prerequisites

- **Blocks implementation:** none identified. No library change or Django model migration is planned.
- **Blocks completion of run A:** `poetry run pytest tests --ignore=tests/e2e`, `npm run jest`, and `poetry run pytest tests/e2e -n 4 --base-url http://localhost:8000` against the intended local interface checkout and its running Django server. The E2E server must use the same local code and test configuration. Rebuild generated CSS with Sass after the SCSS edit.
- **Current workspace gate failures:** the pre-existing editable `efootprint` entry in `pyproject.toml` fails `tests/test_no_dev_dependency.py`; the pre-existing untracked `tools/vscode-plan-review-links/extension.test.js` is discovered by plain Jest but cannot import `vscode`. Product-suite diagnostic runs exclude only those cases. They do not satisfy the plain required commands; clear these conditions before closing run A.
- **Before a commit reaches `main`:** verify `pyproject.toml` and `poetry.lock` reference the PyPI `efootprint` dependency. Both files already have unrelated local edits at task preparation and are outside this working set.
