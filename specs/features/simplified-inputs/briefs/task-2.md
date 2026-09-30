# Task 2 — Fix shared-controller dependent validation

Written 2026-09-30 against e-footprint `96ea0d39` and e-footprint-interface `fe6c04e5`.
Plan: [atomic edit](../plan.html#atomic-edit), [SI-1](../known-issues.md). Task: [overview](../tasks.md#task-2). Status: under review.
Implementation: easy — the wrong dictionary-key check in `attributes_with_depending_values()` is identified; the regression is focused.

## Start here

- Library [`ModelingObject.attributes_with_depending_values()`](../../../../../e-footprint/efootprint/abstract_modeling_classes/modeling_object.py): controller-to-dependent lookup; `check_belonging_to_authorized_values()` consumes it during assignment and `ModelingUpdate`.
- Library [`test_modeling_object.py`](../../../../../e-footprint/tests/abstract_modeling_classes/test_modeling_object.py): current conditional-validation fixtures and dotted-path cases.

## Change along the code path

The helper currently tests `dependent_attribute` for prior membership, then writes under the controller's `depends_on` key. With two dependents on one controller the second overwrites the first. Accumulate under the controller key and add one regression proving both dependents are returned and both matter to validation. Keep this fix in the library so normal Modeling and Simplified inputs share the corrected rule.

## Earlier tasks

None. Task 3's catalog can be built independently but its final shared-controller validation assumes this fix has landed in the local library checkout.

## Reuse

Use the existing `conditional_list_values` shape and `ModelingUpdate`; no interface-side dependency override. The minimal reproduction is recorded in [SI-1](../known-issues.md).

## Invariants and traps

Preserve dependent order and single-dependent behavior. This corrects sibling accumulation only; it neither introduces model-wide selection closure nor a new cycle-rejection policy. Do not alter library serialization.

## Validation

Run `poetry run pytest tests/abstract_modeling_classes/test_modeling_object.py` then full `poetry run pytest` in e-footprint. Assert a controller with two declared dependents returns both and that an invalid value for either is rejected in an appropriate `ModelingUpdate` case.

## Out of scope

No interface catalog or fallback-choice logic.

## Unverified

The recorded reproduction proves the helper defect but does not establish that a shipped class declares this exact sibling arrangement; the regression can use a focused test class.
