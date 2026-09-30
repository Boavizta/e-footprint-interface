# Task 3 — Definition and eligible-field catalog

Repository and implementation range: e-footprint-interface `bcd306eb227692caa79cba81e64e4e00f8852e80..7fc193b11d97e6bb3a44dd533d8e5261aa6836b8`.
Library dependency: e-footprint `99962fad05692c1ab14f1d2a89735eb920347b69`, unchanged by this task.

## Review pointers

- `domain/services/simplified_inputs.py` provides `FieldAddress`, JSON-shaped definition types, `normalize_definition`, `build_catalog(model_web, *, can_edit_timeseries)`, `complete_selection(catalog, selected)` and `validate_definition(catalog, definition)`. Dependency links use actual owners across the flat model inventory; ineligible companions propagate to their controllers. Tests exercise real nested Storage and chained API/linked-job addresses.
- Both repository `interface_config` getters apply `normalize_interface_config` for current-version, missing-key reads as well as older configurations. This is request-local normalization; persisted payloads are not written on read. Task 4 should preserve Session/InMemory parity and their existing config-only save boundaries.
- Task 7 rendering seam: normal `generate_dynamic_form` skips `fixed_nb_of_instances`. Rendering these eligible optional numbers needs a deliberate skip override and empty-value rendering/transport. Task 5 now supplies shared optional-union normalization and empty-value conversion; see its [handoff](task-5.md). Catalog eligibility does not change ordinary form output.

## Design decisions

- [IMPL-DECISION-01](../plan.html#impl-decision-01): constructor-driven catalog eligibility is independent of normal-panel exclusions; Server count remains a required eligible numerical companion.

## Open concerns

- Full non-browser Python validation retains the expected `tests/test_no_dev_dependency.py::TestNoDevDependency::test_no_active_develop_true_in_pyproject` failure because the authorized pre-existing local editable `efootprint` dependency is preserved. Restore published dependency declarations before merge, as recorded in [task gates](../tasks.md#gates).
