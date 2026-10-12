# Task 3 — Reconcile export documentation

Written 2026-10-12 against `e-footprint-interface` commit `07fac466497e63bb8b54ee54183fc91f9665939f` and its current working-tree plan.
Plan: [Delivery](../plan.html#delivery).
Task: [Task 3](../tasks.md#task-3--reconcile-export-documentation).
Status: under review.

## Start here

- Export paragraph after the complete-snapshot boundary — `specs/architecture/persistence.html`: current focus-preservation, save continuation, invalid/rejected cancellation and Configure-exit claims.
- `#simplified-workspace` — `specs/architecture/workspace.html`: module ownership currently includes pending focused-field exports; its every-exit policy includes download.
- E2E rejected-save/focused-export guidance — `specs/testing.md`.
- Download contract and embedded interactive mockup — `specs/features/simplified-inputs/spec.html`; `#exports`, Configure and verification passages — `specs/features/simplified-inputs/plan.html`.
- `CHANGELOG.md` / `AGENTS.md`: consolidated Unreleased behavior entry and “Save-aware export” architecture pointer label.

## Change along the code path

Describe the delivered policy: exports read accepted repository state; ordinary blur/Enter/provenance saves remain; active writes block export; no request, menu opening or download is retained for settlement. Invalid drafts can export previous saved values when idle; server rejection restores accepted fields and a later activation works after error dismissal. Dirty Configure blocks in place with the existing status notice; explicit Save or Cancel → Discard resolves it without export; clean Configure exports without leaving. All other Configure exits retain Save / Discard / Stay.

Replace matching claims in architecture, testing and older Simplified-input feature prose/review guide, including verification descriptions and embedded mockup export policy. Preserve the older guide's structure and unrelated decisions. Link the follow-up where it helps explain a superseded contract; do not keep contradictory present-tense promises. Suggest the AGENTS pointer-label update as required by repository guidance and check whether CLAUDE is a separate file or alias before proposing any duplicate edit.

## Earlier tasks

Task 1 establishes behavior and module ownership; Task 2 verifies native gestures, no-replay, Configure failures and file contents. Use their final evidence and test names when updating references. Do not turn a missing check into a documented success.

## Reuse

Current [feature spec](../spec.html#success), reviewed [plan](../plan.html), owning architecture passages and existing HTML review links. The future `simple-workspace-mutation-gate` artifacts already share this export policy; no rewrite or gate implementation is needed here.

## Invariants and traps

Keep the complete-snapshot server boundary and file formats unchanged. Preserve ordinary native validation feedback; remove only export-specific validation promises. An abandoned press may autosave without exporting. Avoid implying every edit forces a second click: if saving completes before activation, the first activation can work. Keep non-export replay ownership in workspace documentation. Include failed Configure Save remaining dirty/blocked and unfinished Modeling/timeseries exporting saved values. Search beyond headings for stale verification text and mockup messages.

## Validation

Audit `rg -n 'export|download|pendingExport|completeFocusedEditForExport|continueExport'` over affected documentation and feature modules; inspect matches rather than forbidding ordinary words. Open changed HTML and verify source/test links resolve against final files. If mockup script behavior changes, exercise clean/dirty Configure export and ordinary save/export flows in the rendered spec. Check `git diff --check`. No new tests for prose-only edits; retain Task 2's completed product checks unless executable changes require additional verification.

At `feature-implement` close-out the supervisor writes one consolidated `## [Unreleased]` entry; do not duplicate it per task. Standalone `task-implement` follows its immediate changelog gate. Surface the AGENTS/CLAUDE pointer suggestion in the implementation summary.

## Out of scope

Feature archive, deleting old working sets/handoffs, constitution changes, new user controls, revising the mutation-gate scope, product implementation or library documentation.

## Unverified

Final test names and implementation links depend on Tasks 1–2. Resolve them from delivered code during this task; no current plan amendment is needed.
