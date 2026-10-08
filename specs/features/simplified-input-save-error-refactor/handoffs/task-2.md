# Task 2 — Restore accepted Simplified fields on rejected saves

Repository and implementation range: `e-footprint-interface` `4d299c1db9a9357a59151b6a69633bbc01c8b874..567b5f0fd44043b75441950850c1d81648e73b49`.

## Review pointers

- `_rejected_simplified_input()` creates a fresh active repository and `ModelWeb` after the exception. `render_input_fields_oob()` shares the successful field renderer without adding total or Results fragments. View tests cover rejected value/provenance mutations before persistence and presentation failures after persistence.
- After `execute()` returns, late presentation failure restores its `output.changed_fields`, including persisted conditional dependents. Earlier failures restore only the submitted address. The boundary case is on-premise → autoscaling resetting an authored instance count.
- Error responses leave quick totals and open Results at their prior rendered calculation even if persistence succeeded; a subsequent successful calculation render refreshes them from the accepted model.
- Mutation completion finds the replacement inline form by its value prefix; timeseries completion finds its field by owner/attribute and closes the panel. Focused export checks native validity before setting its pending continuation.
- Task 3 should replace `fail_lifespan_edit()`'s `route.abort()` with the new `reject_simplified_edit()` helper for its navigation/export journeys. A network abort cannot deliver the accepted-field OOB fragment. Broad failed-draft guard deletions and their other browser assertions remain Task 3's working set.

## Open concerns

- Implemented; complete workspace validation remains pending the [recorded gate prerequisites](../tasks.md#gates-and-prerequisites). Plain non-E2E pytest fails `tests/test_no_dev_dependency.py` on the pre-existing editable dependency; plain Jest fails the pre-existing untracked VS Code extension suite because `vscode` is unavailable. The narrow diagnostic exclusions do not satisfy those required commands. Task 3 owns the full E2E gate.
