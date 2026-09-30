# Task 5 — Apply one atomic selected-input edit

Repositories and implementation ranges:
- e-footprint-interface `d17c0e58de627fa7562288d931e37b03540148d8..c04add4a09af3df9add6eaf5be53874c8be5b025`.
- e-footprint `a76ce657a1eae98f6b6ecb727d7378e35010e11e..8aa6683738226d73908f98e0d98bb04616172d7a`.

## Review pointers

- `EditSimplifiedInputUseCase(model_web, catalog).execute(EditSimplifiedInput(address, parsed_value))` accepts normalized
  explainable data, a reference ID, or a reference-ID list. It requires an eligible selected address, reconciles
  conditional dependents against candidate values across actual owners, and applies one library transaction followed
  by one persistence. `SimplifiedInputsOutput.changed_fields` includes retained dependents whose options changed;
  same-value/provenance-only saves return only the submitted address.
- `prepare_input_changes()` is shared with normal editing. Replacement values inherit omitted provenance and their
  existing label. Metadata-only and same-value changes use the existing request-local metadata patching path; failure
  must discard that ModelWeb rather than reuse it for another save.
- `resolve_optional_annotation()` now unwraps unions admitting `EmptyExplainableObject`, including Server count.
  Task 7 still owns the normal-panel skip override and rendering/transport of optional empty controls. The use case
  accepts normalized empty data as `{"value": null}` and converts fallback metadata choices through the same preparer.

## Design decisions

- [IMPL-DECISION-03](../plan.html#impl-decision-03): the library's `input_values_match()` distinguishes empty input
  absence from explicit zero and compares authored timeseries builder/form inputs before numerical equality.
  Transaction no-ops, allowed-value validation, interface preparation and conditional reconciliation share that rule;
  arithmetic equality remains unchanged.

## Open concerns

- Full non-browser interface validation retains the expected
  `tests/test_no_dev_dependency.py::TestNoDevDependency::test_no_active_develop_true_in_pyproject` failure because the
  authorized pre-existing editable dependency declarations remain untouched. Restore published declarations before
  merge, as recorded in [task gates](../tasks.md#gates).
- Full browser validation belongs to the Run A global review; this task adds no browser surface.
