# Task 4 — Save configuration and exchange independent models

Repository and implementation range: e-footprint-interface
`9e94e06da77922c2f087a246d59ee94cd800723a..8e881aaab1e5f1ca964f05e2edc3c0fd88c6f510`.
Library dependency: e-footprint `99962fad05692c1ab14f1d2a89735eb920347b69`, unchanged by this task.

## Review pointers

- `UpdateSimplifiedDefinitionUseCase(repository, catalog).execute(settings, replace=False)` takes the caller's
  catalog, completes required companions, rejects an explicitly excluded locked companion, and returns
  `SimplifiedInputsOutput(notices, changed_fields)`. Replacement saves return `changed_fields=None`; inline
  saves report every changed address. Excluded entries retain authored help; empty excluded entries are removed.
- Session config fallback uses the existing session key with per-slot `{system_id, config, version}` records.
  Reads require the current slot's System ID; clear removes only that slot's record. Config saves preserve both
  backend representations and adjust indexed canonical weight when only compact recovery remains available.
- `_restore_workspace` imports every model, remaps colliding System IDs, measures final canonical documents,
  and prepares slot-0 recovery before clears. `SystemImportService` remains unchanged and does not validate
  definitions. Duplication and single-model import adopt copied/remapped interface settings.

## Open concerns

- Full non-browser Python validation retains the expected
  `tests/test_no_dev_dependency.py::TestNoDevDependency::test_no_active_develop_true_in_pyproject` failure
  because authorized pre-existing local editable dependency declarations remain untouched. Restore published
  declarations before merge, as recorded in [task gates](../tasks.md#gates).
- Full browser validation belongs to the Run A global review; this task introduces no browser surface.
