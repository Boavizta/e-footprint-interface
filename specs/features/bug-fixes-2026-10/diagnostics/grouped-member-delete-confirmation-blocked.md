# Grouped edge members are blocked before their deletion hook

**Status:** newly observed pre-existing defect, outside Run A; not fixed or assigned to this run.

Discovered during Task 11 review on 2026-11-03. The reviewer ran the baseline
(`8da403d5`) and Task 11 (`47a9f48d`) confirmation implementations against the same
ordinary group-membership graph. Both returned `(False, ['Parent group'])` for a
grouped custom edge device and a nested edge device group.

## Reproduction shape

Using `ModelWeb.add_new_efootprint_object_to_system`, add an empty custom
`EdgeDevice`, a parent `EdgeDeviceGroup` named `Parent group`, and a child
`EdgeDeviceGroup`. Set `parent.edge_device_counts[device]` and
`parent.sub_group_counts[child]` to `SourceValue(1 * u.dimensionless)`. Call
`DeleteObjectUseCase.check_can_delete` for the device and child group. Both are
blocked by their parent despite the existing deletion hook supporting unlinking.

This was a scratch diagnostic, not a new committed regression test. Existing
integration coverage executes deletion directly and does not establish that the
confirmation path permits it.

## Cause and follow-up

[`_container_removal_targets`](../../../../model_builder/application/use_cases/delete_object.py)
excludes dict memberships for wrappers declaring `handles_own_dict_memberships`.
The residual-reference check in `check_can_delete` consequently treats the parent
group as a blocker. However,
[`EdgeGroupMemberMixin.pre_delete`](../../../../model_builder/domain/entities/web_core/hardware/edge/edge_group_member_mixin.py)
explicitly removes the object from its parent-group dictionaries.

A future fix needs confirmation semantics that recognize hook-managed group
memberships while retaining independent reference blockers. Add a normal
confirmation-then-execution regression when that fix is approved. Task 11's
confirmation changes and the existing execution hook remain unchanged for this report.
