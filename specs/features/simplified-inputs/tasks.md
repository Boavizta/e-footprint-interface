# Simplified inputs — tasks

Spec: [spec.html](spec.html) · Plan: [plan.html](plan.html) · Confirmed library issue: [SI-1](known-issues.md)

Status: Runs A–C complete, including independent task and global reviews. This is one interface-owned, cross-repository working set. The deployment/merge prerequisite below remains outstanding.

Human review: the user prefers one consolidated review after implementation of Runs A–C. No intermediate human review is required before Runs B or C; independent task and global agent reviews still apply to each run.

## Runs

- **Run A — foundations:** Tasks 1–5 complete.
- **Run B — authoring:** Tasks 6–8 complete, including global review.
- **Run C — consumption:** Tasks 9–10.

## Overview

| Task | Delivered behavior | Plan section | Repository | Implementation |
|---|---|---|---|---|
| [1](#task-1) | Ready-made modelings become Examples throughout the catalog and docs | [1.6](plan.html#examples) | Both | easy — fixed rename map and explicit template-name boundary |
| [2](#task-2) | One controller validates every dependent | [1.4](plan.html#atomic-edit) | Library | easy — identified wrong-key check and focused regression |
| [3](#task-3) | Field identity, eligibility, required-selection closure and empty definition | [1.1](plan.html#contract), [1.2](plan.html#dependencies) | Interface | standard — integrate constructor metadata, form fields and builder lookup |
| [4](#task-4) | Per-model configuration saves, copies and safe file exchange | [1.2](plan.html#configuration-save), [1.5](plan.html#persistence) | Interface | standard — extend existing config save, slot/ID helpers and import preflight |
| [5](#task-5) | Atomic selected-input value and provenance changes across owners | [1.4](plan.html#atomic-edit) | Both | hard — the plan fixes one batch and request-local persistence, Tasks 2–3 supply validation and field links, and existing code supplies conversion/rollback; deriving chained cross-owner candidates and coordinating metadata remains demanding because validation reads the applied graph |
| [6](#task-6) | One workspace mutation in flight, preserving disabled states | [1.4](plan.html#saves) | Interface | standard — extend existing HTMX lifecycle and disabled-state snapshot to mutation triggers |
| [7](#task-7) | Configure, navigation, base-view switching and draft exit | [1.2](plan.html#workspace), [1.5](plan.html#model-context) | Interface | standard — join Task 3/4 data and save APIs with the existing deferred-navigation pattern |
| [8](#task-8) | Inline bookmarks and creation/deletion selection lifecycle | [1.3](plan.html#lifecycle) | Interface | standard — Task 3/4 APIs and creation's final save cover the lifecycle; map draft fields to final IDs |
| [9](#task-9) | Simple value/provenance editing and live totals in Simplified inputs | [1.4](plan.html#consume) | Interface | standard — connect Task 5/6/7 outputs through existing modal and OOB rendering paths |
| [10](#task-10) | Focused timeseries, export completion and final integrated verification | [1.4](plan.html#timeseries), [1.5](plan.html#exports), [3](plan.html#verification) | Interface | standard — use current timeseries registry/panel and Task 6/9 save state for export |

The [agent tooling](../../agent-tooling.md) routes easy, standard and hard to their matching implementer roles. `task-review` chooses review depth independently from the implementation tier and actual diff.

## Task 1 — Rename ready-made modelings to Examples

Goal: Complete the coordinated terminology and API cutover while preserving scenario IDs, data, results and guide associations. Status: complete. Brief: [task-1](briefs/task-1.md).

Repository: e-footprint and e-footprint-interface. Files touched: library `efootprint/modeling_templates/`, `tests/test_modeling_templates.py`, package resources, live docs; interface catalog, picker, routes, tour/help, authoring scripts, callers and tests. Tests: both catalog suites, package-resource and deep-link checks, full suites and library strict docs build. Acceptance: renamed imports/commands/picker/deep links work from installed artifacts; historical content and Django rendering-template names remain intact. Depends on: none. Implementation: easy — the rename map and Django rendering-template boundary are explicit.

## Task 2 — Fix shared-controller dependent validation

Goal: Correct [SI-1](known-issues.md) in the library without an interface workaround. Status: complete. Brief: [task-2](briefs/task-2.md).

Repository: e-footprint. Files touched: `efootprint/abstract_modeling_classes/modeling_object.py`, `tests/abstract_modeling_classes/test_modeling_object.py`. Tests: focused sibling-dependent regression and library suite. Acceptance: two conditional fields with one controller are both returned and both checked by the existing validator. Depends on: none. Implementation: easy — the wrong dictionary-key check in `attributes_with_depending_values()` is identified; the regression is focused.

## Task 3 — Establish the definition and eligible-field catalog

Goal: Give every model an empty-capable definition and derive eligible fields and required companions from existing modeling metadata. Status: complete. Brief: [task-3](briefs/task-3.md).

Repository: e-footprint-interface. Files touched: new `domain/services/simplified_inputs.py` and `domain/conditional_inputs.py`; form generator, timeseries registry, version normalization and focused tests. Tests: eligibility, nested owner addresses, dependent-only/chained selection, normal form and timeseries regressions. Acceptance: address keys are owner ID plus constructor attribute; unsupported structural fields stay excluded; `complete_selection` and validation agree; older files normalize to empty without copying values. Depends on: Task 2 for final shared-controller verification. Implementation: standard — integrate existing constructor/conditional metadata, form fields and timeseries builder lookup into one catalog.

## Task 4 — Save configuration and exchange independent models

Goal: Persist definition replacements and inline patches without recomputing the model; preserve distinct definitions through duplication and file round-trips. Status: complete. Brief: [task-4](briefs/task-4.md).

Repository: e-footprint-interface. Files touched: new `application/use_cases/simplified_inputs.py`; session/in-memory/workspace repositories; `views.py`, `views_workspace.py`, version normalization and repository/workspace tests. Tests: replacement versus patch, retained help/Clear, budget failure, per-slot recovery, independent duplicate, System-ID remapping, two-model import failure and round-trip. Acceptance: a failed configuration save publishes nothing; every file carries its model's definition; incoming models and combined size are checked before live workspace replacement. Depends on: Task 3. Implementation: standard — extend `save_interface_config()`, slot/ID helpers and `SystemImportService`; preflight both models before the current restore writes.

## Task 5 — Apply one atomic selected-input edit

Goal: Save a controlling field, all affected dependent values and provenance with one library `ModelingUpdate`. Status: complete. Brief: [task-5](briefs/task-5.md).

Repository: both. Files touched: interface `domain/object_factory.py`, `application/use_cases/simplified_inputs.py`, integration tests; library authored-input matching, conditional validation and transaction regressions. [IMPL-DECISION-03](plan.html#impl-decision-03) covers confirmed authored-state changes hidden by numerical equality. Tests: valid-dependent retention, first-allowed fallback, empty-choice rejection, no partial value/metadata persistence, nested owner and empty-count cases. Acceptance: one accepted batch persists once; failure preserves saved values and metadata; normal edit behavior remains intact. Depends on: Tasks 2 and 3. Implementation: hard — the plan fixes one batch and request-local persistence, Tasks 2–3 supply sibling validation and field links, and the existing factory/`ModelingUpdate` supply conversion and rollback. The implementer must derive chained, cross-owner candidate values and coordinate direct metadata changes before that batch; this is demanding because conditional validation reads the applied graph while the current converter invokes `ModelingUpdate` per owner.

## Task 6 — Guard workspace mutations

Goal: Allow only one mutation at a time across existing Modeling and new simplified-input controls. Status: complete. Brief: [task-6](briefs/task-6.md).

Repository: e-footprint-interface. Files touched: `theme/static/scripts/model_builder_main.js`, related shell controls and Jest/E2E guard tests. Tests: delayed mutation blocks editing, switching and export; disabled-state restoration and failure unlock. Acceptance: no second mutation or queued edit starts while one is active; read/scroll and stateless preview remain available. Depends on: none; land before Tasks 7–10. Implementation: standard — extend current HTMX request hooks and per-XHR disabled-state snapshot to mutation controls and response settlement.

## Task 7 — Build Configure and the shared workspace

Goal: Render eligible fields in the grouped Configure view and saved fields in a Simplified inputs view, with navigation and explicit configuration save/exit. Status: complete. Brief: [task-7](briefs/task-7.md).

Repository: e-footprint-interface. Files touched: new simplified-input views, presenter, partials, JS and SCSS; URLs, model shell, toolbar and presenter/Jest/E2E tests. Tests: grouping, filter/focus, conditional draft locks, Clear, Save/Discard/Stay, per-model base view and fresh render on Modeling entry. Acceptance: Configure saves a complete definition and returns a complete selected-field view; leaving dirty Configure cannot discard changes silently; old form values stay in DOM only. Depends on: Tasks 3, 4 and 6. Implementation: standard — combine Task 3/4 catalog and save APIs with `side_panel_utils.js`'s deferred-action pattern and resident-canvas switching.

## Task 8 — Author selection beside Modeling inputs

Goal: Provide immediate bookmarks for existing fields, provisional bookmarks for new objects and deletion cleanup. Status: complete. Brief: [task-8](briefs/task-8.md).

Repository: e-footprint-interface. Files touched: form/source-row contexts, shared bookmark partial, create/edit/delete use cases and views, deletion modal, simplified-input JS, tests. Tests: true nested owner, independent inline patch, Undo, creation required-field preview/lock, successful create, failed/cancelled create, cascade pruning and warning. Acceptance: bookmark saves never submit unsaved value drafts; creation settings persist only after success; deletion removes selected and retained-help entries for removed owners. Depends on: Tasks 3, 4, 6 and 7. Implementation: standard — Task 3/4 provide addresses and patches, and `CreateObjectUseCase` has one final save after request-local hooks; map draft fields to created IDs and use deletion's actual cascade.

## Task 9 — Edit simple selected inputs and refresh totals

Goal: Autosave scalar/select/provenance edits from Simplified inputs and show the accepted footprint in both Results controls. Status: complete. Brief: [task-9](briefs/task-9.md).

Repository: e-footprint-interface. Files touched: simplified-input endpoints/presenter/field partials, error modal path, source metadata JS, OOB results renderer, modeling-object hooks and tests. Tests: Enter/blur deduplication, targeted updates, error-modal failure despite HTTP 200, preserved draft, both totals after successful mutations and last-saved total on failure. Acceptance: hidden fields are not offered by the view; accepted edits refresh only affected controls/results; failed edits remain visible and retryable. Depends on: Tasks 5–8. Implementation: standard — connect Task 5/6/7 outputs through existing error-modal signals, targeted swaps and Results OOB rendering.

## Task 10 — Complete timeseries, export and release checks

Goal: Finish focused timeseries editing and make every normal export follow completed simplified-input saves; verify the full feature. Status: complete. Brief: [task-10](briefs/task-10.md). [IMPL-DECISION-08](plan.html#impl-decision-08) records failed-edit recovery before changing views.

Repository: e-footprint-interface, with both repositories' release gates. Files touched: timeseries side-panel partial and view wiring, simplified-input/export JS, existing download controls, critical E2E tests, changelogs and owning architecture/design/docs pages. Tests: strategy switch/preview/Save/Cancel, failed panel preservation, model-switch discard, focused edit then export, two-model export, full interface Python/Jest/E2E gates, full library pytest and strict docs/package checks. Acceptance: no export claims an unsaved simplified edit; all agreed user journeys pass; the PyPI dependency is restored in both `pyproject.toml` and `poetry.lock` before any merge to main. Depends on: Tasks 1–9. Implementation: standard — use the existing timeseries registry/panel and Task 6/9 save state in current export controls, then run integrated gates.

## Gates

- **Local development:** keep `efootprint = {path = "../e-footprint", develop = true}  # local dev: swap back, do NOT commit` active throughout Runs B–C. Preserve the local `pyproject.toml` and `poetry.lock` edits and exclude them from commits. The dependency guard's expected local failure does not block implementation or human review; restore the published dependency during release/merge preparation.
- **Deployment/merge prerequisite:** pre-existing editable `pyproject.toml` and `poetry.lock` edits are preserved for local co-development; the dependency guard therefore remains failing locally. Before any commit reaches `main`, publish/use an `efootprint` release containing the Examples API and authored-input matching changes, then restore a matching PyPI dependency in both files and pass the dependency guard.
- **Final environment:** use the intended local library checkout for cross-repo tests. Interface E2E requires a running local server; no production service. Full interface pytest and Jest, library pytest, strict MkDocs and installed-resource checks are final quality gates. Add consolidated Unreleased changelog entries and promote new patterns to the owning architecture pages; suggest the matching `AGENTS.md`/`CLAUDE.md` pointers.
