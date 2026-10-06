# Derived optional quantity controls — tasks

Plan and approved scope: [plan.html](plan.html) · Separate spec: none
Status: implementation and review complete — deployment dependency pending.

## Implementation runs

| Run | Delivered milestone | Tasks in execution order | Prerequisites |
|---|---|---|---|
| A — feature implementation | Optional count units and validation feed type-derived normal and simplified controls. | [1](#task-1--declare-and-validate-optional-quantity-units) → [2](#task-2--render-and-save-derived-optional-controls) | Task 2 uses Task 1's library checkout. |

## Overview

| Task | Delivered behavior | Plan section | Repository | Implementation |
|---|---|---|---|---|
| [1](#task-1--declare-and-validate-optional-quantity-units) | Shared unit metadata and correct optional quantity validation. | [1.1](plan.html#metadata), [1.3](plan.html#edit) | `e-footprint` | standard |
| [2](#task-2--render-and-save-derived-optional-controls) | Type-derived “Leave unset” controls in both forms, with correct empty and numeric saves. | [1.2](plan.html#forms), [1.3](plan.html#edit) | `e-footprint-interface` | standard |

## Task 1 — Declare and validate optional quantity units

Goal: Give optional instance counts a single declared unit and apply the same dimensionality and sign checks to nonempty updates that ordinary quantities receive.
Status: implemented and reviewed.
Brief: [briefs/task-1.md](briefs/task-1.md)
Repository: `e-footprint`.
Files touched: `efootprint/utils/tools.py`; `efootprint/core/hardware/{hardware_base,server_base,server,gpu_server,storage}.py`; `efootprint/builders/hardware/{boavizta_cloud_server,boavizta_server_from_config}.py`; `efootprint/abstract_modeling_classes/modeling_object.py`; `tests/abstract_modeling_classes/test_modeling_update.py`; `specs/architecture/layers-and-modeling.html`.
Tests: targeted ModelingUpdate tests for declared/default units, compatible and incompatible units, empty values, missing declarations, negative values and count JSON round-trip; then full `poetry run pytest` and `mkdocs build --strict` in the library checkout.
Acceptance: `get_init_signature_params()` still exposes resolved ordinary types; the quantity member of all six count constructors carries `InputUnit(u.concurrent)`; a class quantity default takes precedence over annotation metadata; missing unit sources raise a descriptive `TypeError` even for an empty update; compatible nonnegative counts and empty values succeed, while incompatible units and negative counts fail; count serialization remains stable.
Depends on: none; the plan is approved.
Implementation: standard — the unit lookup must coordinate class defaults with `Annotated` metadata while preserving the existing resolved-annotation callers and model validation behavior.

## Task 2 — Render and save derived optional controls

Goal: Make normal and simplified quantity editors show a generic unset switch only when the constructor allows an empty value, with no instance-specific UI flag or copy.
Status: implemented and reviewed.
Brief: [briefs/task-2.md](briefs/task-2.md)
Repository: `e-footprint-interface`.
Files touched: `model_builder/adapters/forms/form_field_generator.py`; `model_builder/adapters/ui_config/field_ui_config.json`; `model_builder/templates/model_builder/side_panels/dynamic_form_fields/explainable_quantity.html` and new `optional_explainable_quantity.html`; `model_builder/templates/model_builder/simplified_inputs/editor.html` and new `explainable_quantity.html` and `optional_explainable_quantity.html`; `theme/static/scripts/{optional_quantity,simplified_inputs}.js`; `tests/fixtures/form_data_builders.py`; `tests/unit_tests/adapters/forms/test_form_field_generator.py`; `tests/unit_tests/domain/entities/class_structures/{ServerWeb,StorageWeb}_creation_structure.json`; `js_tests/dynamic_forms.test.js`; `tests/integration/test_simplified_inputs.py`; `tests/e2e/test_simplified_inputs.py`; `specs/architecture/forms-and-relationships.html`. Adjust existing parser tests only if the unchanged blank-versus-zero contract needs additional coverage.
Tests: generator and template assertions for optional and ordinary quantities, default and annotation unit sources, absent units and conditional lock; existing parser and integration coverage for blank versus zero and fixed-count persistence; Jest controller and empty-change tests; one normal/simplified Playwright journey; full interface pytest suite and `npm run jest` against the Task 1 library checkout.
Acceptance: optional quantities select the optional partial, ordinary quantities keep a required plain number, and empty values use a class quantity default or `InputUnit` instead of UI config or `dimensionless`; a saved number opens with the switch off and blank opens with it on; “Leave unset” and the existing tooltip carry the explanation; autoscaling and serverless force empty; the simplified switch saves empty immediately; number entry saves normally; no `auto_*`, `auto_sizing`, `empty_unit`, or instance-specific helper text remains in active form code or snapshots.
Depends on: Task 1's expected-unit lookup and annotated count constructors.
Implementation: standard — the established generator, templates and shared switch script must be updated together across normal and simplified form lifecycles.

## Outstanding prerequisite

- **Deployment only:** release the library version containing `get_expected_input_unit` and the annotated count constructors, then update the interface's committed PyPI `efootprint` dependency and lockfile from 25.0.0. The pre-existing local editable dependency edits remain uncommitted for co-development.
