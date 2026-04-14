"""Domain service for attaching a newly created edge device or edge device group
to existing parent edge device groups.
"""
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup


PARENT_GROUP_MEMBERSHIPS_FIELD = "parent_group_memberships"


def apply_parent_group_memberships_from_form_data(added_obj, form_data: dict, model_web) -> None:
    """Link `added_obj` into the parent groups listed in the pre-parsed
    `parent_group_memberships` mapping.

    `form_data[PARENT_GROUP_MEMBERSHIPS_FIELD]` is a `{parent_group_id: count}` dict
    already parsed by the adapter layer.
    """
    memberships = form_data.get(PARENT_GROUP_MEMBERSHIPS_FIELD) or {}
    if not memberships:
        return

    member_obj = added_obj.modeling_obj
    for parent_id, count in memberships.items():
        parent_group = model_web.get_efootprint_object_from_efootprint_id(parent_id, "EdgeDeviceGroup")
        if not isinstance(parent_group, EdgeDeviceGroup):
            raise ValueError(f"Parent {parent_id} is not an EdgeDeviceGroup.")
        target_dict = _pick_target_dict(parent_group, member_obj)
        target_dict[member_obj] = SourceValue(count * u.dimensionless)


def _pick_target_dict(parent_group: EdgeDeviceGroup, member_obj):
    if isinstance(member_obj, EdgeDeviceGroup):
        return parent_group.sub_group_counts
    if isinstance(member_obj, EdgeDevice):
        return parent_group.edge_device_counts
    raise ValueError(
        f"Object of type {type(member_obj).__name__} cannot be linked into an edge device group.")
