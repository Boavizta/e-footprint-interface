# Task 1 — Declare and validate optional quantity units

Written 2026-10-06 against `e-footprint` `984f8b39` and `e-footprint-interface` `2e64a861` (both have unrelated local dependency edits).
Plan: [model contract](../plan.html#metadata), [edit validation](../plan.html#edit). Task: [Task 1](../tasks.md#task-1--declare-and-validate-optional-quantity-units).
Status: under review; the plan is the approved scope, and the task breakdown awaits review.

## Start here

- `get_init_signature_params()` — `e-footprint/efootprint/utils/tools.py` — currently calls `get_type_hints()` without extras and returns a `Signature.parameters` mapping; existing runtime type consumers need that shape.
- `HardwareBase` — `e-footprint/efootprint/core/hardware/hardware_base.py` — suitable home for the shared count quantity alias; its concrete constructor consumers are `ServerBase`, `Server`, `GPUServer`, `Storage`, `BoaviztaCloudServer` and `BoaviztaServerFromConfig`.
- `ModelingObject._check_input_value_positivity_and_unit()` — `e-footprint/efootprint/abstract_modeling_classes/modeling_object.py` — currently returns for union annotations before dimensionality and sign checks. `check_input_value()` calls type checking first, then this method.
- `TestModelingUpdate` — `e-footprint/tests/abstract_modeling_classes/test_modeling_update.py` — already covers empty versus zero, conditional count changes, rollback and JSON round-trip.

## Change along the code path

Introduce `InputUnit` and an expected-unit lookup in `tools.py`. Read a unit-bearing `cls.default_values[param]` first; otherwise inspect `get_type_hints(cls.__init__, include_extras=True)` and the quantity member's metadata. Do not treat `EmptyExplainableObject.unit` as a declaration. Keep `get_init_signature_params()` unchanged so existing `issubclass` and union-member code still receives ordinary types. Put `InstanceCountQuantity = Annotated[ExplainableQuantity, InputUnit(u.concurrent)]` in `hardware_base.py`; replace only the quantity member for the six count declarations and retain the builder `| None` members. See [plan §1.1](../plan.html#metadata).

In `_check_input_value_positivity_and_unit()`, recognize the optional quantity union, resolve its expected unit before accepting an empty value, and reject missing sources with class and parameter in the error. For a nonempty scalar quantity, compare dimensionality and enforce the existing negative-value policy. Leave ordinary quantity checks based on `default_values` and preserve other union behavior. See [plan §1.3](../plan.html#edit).

## Earlier tasks

None. Task 2 will consume this helper and the annotated constructors; the helper name and import location should be stable at handoff.

## Reuse

Use the existing `get_init_signature_params()` and `ModelingUpdate` validation path. `ServerBase.conditional_list_values` already restricts autoscaling and serverless counts to `EmptyExplainableObject`. `system_to_json()`/`json_to_system()` already provide the count round-trip path; no new serialization shape is planned.

## Invariants and traps

- The framework layer must not import hardware or other `core` modules. The metadata/helper live in `utils/tools.py` for both framework and core callers.
- The six constructors redeclare the same parameter; metadata on a base constructor alone would not reach the concrete class inspected by the interface.
- `Server`, `GPUServer` and both builders currently have empty count defaults; `Storage.default_values` omits the count. `EmptyExplainableObject` is unit-neutral, so these need annotation fallback.
- A class quantity default wins over annotation metadata; a saved nonempty value is still checked against the declared expected dimensionality.

## Validation

Extend `tests/abstract_modeling_classes/test_modeling_update.py` with targeted updates for compatible/incompatible units, negative values, empty values, default priority and missing declarations (including an empty update). Retain the existing zero/empty and JSON round-trip assertions. Run `poetry run pytest tests/abstract_modeling_classes/test_modeling_update.py`, `poetry run pytest`, and `mkdocs build --strict` from `e-footprint`; update `specs/architecture/layers-and-modeling.html#units` with the fallback rule. The full suite and docs build are required implementation gates, not claims made by this brief.

## Out of scope

No UI config, templates, browser scripts, parser branch, unit-bearing empty serialization or annotation for every ordinary quantity. Interface work belongs to Task 2.
