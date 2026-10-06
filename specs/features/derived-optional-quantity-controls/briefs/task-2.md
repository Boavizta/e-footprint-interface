# Task 2 — Render and save derived optional controls

Written 2026-10-06 against `e-footprint` `984f8b39` and `e-footprint-interface` `2e64a861` (both have unrelated local dependency edits).
Plan: [forms](../plan.html#forms), [edit behavior](../plan.html#edit). Task: [Task 2](../tasks.md#task-2--render-and-save-derived-optional-controls).
Status: under review; the plan is the approved scope, and the task breakdown awaits review.

## Start here

- `generate_dynamic_form()` — `e-footprint-interface/model_builder/adapters/forms/form_field_generator.py` — already detects `allows_empty` from the constructor union, derives empty-only controller values, and routes quantity fields through one dictionary.
- `dynamic_form_field.html` and `explainable_quantity.html` — `model_builder/templates/model_builder/side_panels/dynamic_form_fields/` — the first routes by `input_type`; the second currently mixes the number with instance-specific switch markup.
- `editor.html` — `model_builder/templates/model_builder/simplified_inputs/` — currently embeds a second copy of the number and switch under the plain quantity branch.
- `optional_quantity.js` and `simplified_inputs.js` — `theme/static/scripts/` — the shared handler clears/hides numbers and forces empty for controller values; the simplified listener saves only when the current event detail says `automatic`.
- `create_post_data_from_class_default_values()` — `tests/fixtures/form_data_builders.py` — currently gets empty units from `FieldUIConfigProvider`, falling back to `dimensionless`.

## Change along the code path

Consume Task 1's expected-unit helper from the library. In `generate_dynamic_form()`, select `optional_explainable_quantity` for quantity unions containing `EmptyExplainableObject`, keep `explainable_quantity` for ordinary quantities, and use the class default or `InputUnit` when the saved value is empty. Keep a nonempty saved value's actual display unit. Rename `auto_*` controller keys to empty-state names and keep the direct `depends_on` constraint; the plan requests a short comment that dotted paths need separate handling. Remove `auto_sizing`, `empty_unit` and the instance-specific placeholder from `field_ui_config.json`; retain `step` and `hide_unit`. The test form-data builder uses the same expected-unit helper for empty defaults. See [plan §1.2](../plan.html#forms).

Split normal form markup into a plain numeric partial and an optional wrapper that includes it; the existing dynamic-field router needs no new branch. Split simplified editor markup into corresponding numeric and optional partials, with `editor.html` dispatching both types. Keep the switch and controller attributes only in the optional wrappers, use generic “Leave unset” copy, and leave parameter meaning to the existing field tooltip. Rename the shared script's `auto_*` selectors/action and `optional-quantity:changed` detail to `empty`; update `simplified_inputs.js` to save when switched to empty. Keep its number focus/required/clear behavior and the existing parser's blank-versus-zero contract. See [plan §1.3](../plan.html#edit).

## Earlier tasks

Task 1 supplies `InputUnit`, one expected-unit lookup, and annotated count constructors. It does not change form dictionaries or markup. Use the delivered helper rather than duplicating annotation inspection in the interface; if its final symbol name differs from the proposed name, import the actual exported symbol.

## Reuse

`dynamic_form_field.html` already includes `field.input_type` dynamically. `resolve_optional_annotation()` leaves a single editable value type for the generator while the original constructor union remains available for `allows_empty`. `form_data_parser.py` already distinguishes blank from zero. `FormContextBuilder.build_input_fields()` reuses the same generator for simplified fields; `EditSimplifiedInputUseCase` already persists accepted changes.

## Invariants and traps

- A saved empty value cannot supply a unit; do not read its neutral `unit` or silently substitute `dimensionless`.
- A saved number opens with the switch off and a required number; blank opens with the switch on. Plain quantities always keep their required numeric input.
- The controller may force empty for autoscaling/serverless. `optional_quantity.js` must clear the value and disable the switch in that state; the existing JS test exercises this.
- The simplified editor's unit travels in a hidden input; the normal form's unit input is readonly. Both must submit the expected unit after an empty value is toggled to a number.
- Existing `pyproject.toml` and `poetry.lock` use a local editable library dependency for co-development. Preserve those working-tree edits during preparation and testing, then restore a valid PyPI dependency deliberately before committing interface changes.

## Validation

Extend `tests/unit_tests/adapters/forms/test_form_field_generator.py` to assert both input types, template markup, generic copy, direct controller lock, class-default/annotation unit precedence and missing-source error; refresh `ServerWeb` and `StorageWeb` creation-structure snapshots. Keep or extend `tests/unit_tests/adapters/forms/test_form_data_parser.py` blank/zero assertions only as needed. Use `tests/integration/test_simplified_inputs.py` for accepted numeric/empty saves and conditional reconciliation, `js_tests/dynamic_forms.test.js` for the renamed controller/action/event, and `tests/e2e/test_simplified_inputs.py::TestSimplifiedInputs::test_instance_sizing_switch_in_modeling_and_simplified_inputs` for one visible normal/simplified journey; update that test to generic selectors/copy and confirm saved fixed and empty states. Run targeted suites, then `poetry run pytest tests --ignore=tests/e2e`, `npm run jest`, and `poetry run pytest tests/e2e -n 4` with a local server using the Task 1 library checkout. Update `specs/architecture/forms-and-relationships.html#simplified-input-catalog` to describe type-derived optionality and unit metadata.

## Out of scope

No second optionality tag, parser branch, persistence format, dotted-path controller implementation or library model validation; Task 1 owns the latter.

## Unverified

The full browser flow and test gates have not been run during task preparation.
