"""Domain service for attaching a newly created edge device or edge device group
to existing parent edge device groups, based on a JSON payload produced by the
creation-panel dict_count widget.
"""
import json
from typing import Any

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup


PARENT_GROUP_MEMBERSHIPS_FIELD = "parent_group_memberships"


def apply_parent_group_memberships_from_form_data(added_obj, form_data: dict, model_web) -> None:
    """Read the `parent_group_memberships` field from form_data and link the new
    object into the selected parent groups with their requested counts.

    `added_obj` is the web wrapper returned by `add_new_efootprint_object_to_system`.
    `form_data` carries the widget's hidden-input value as a JSON-encoded
    `{parent_group_id: count}` mapping.
    """
    raw = form_data.get(PARENT_GROUP_MEMBERSHIPS_FIELD)
    memberships = _parse_memberships(raw)
    if not memberships:
        return

    member_obj = added_obj.modeling_obj
    for parent_id, count in memberships.items():
        parent_group = model_web.get_efootprint_object_from_efootprint_id(parent_id, "EdgeDeviceGroup")
        if not isinstance(parent_group, EdgeDeviceGroup):
            raise ValueError(f"Parent {parent_id} is not an EdgeDeviceGroup.")
        target_dict = _pick_target_dict(parent_group, member_obj)
        target_dict[member_obj] = SourceValue(_parse_count(count) * u.dimensionless)


def _parse_memberships(raw: Any) -> dict:
    if raw in (None, ""):
        return {}
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{PARENT_GROUP_MEMBERSHIPS_FIELD} must be valid JSON.") from exc
    else:
        parsed = raw
    if not isinstance(parsed, dict):
        raise ValueError(f"{PARENT_GROUP_MEMBERSHIPS_FIELD} must be a JSON object.")
    return parsed


def _parse_count(raw_count: Any) -> int:
    try:
        count = int(raw_count)
    except (TypeError, ValueError) as exc:
        raise ValueError("Parent group membership count must be an integer.") from exc
    if count < 1:
        raise ValueError("Parent group membership count must be at least 1.")
    return count


def _pick_target_dict(parent_group: EdgeDeviceGroup, member_obj):
    if isinstance(member_obj, EdgeDeviceGroup):
        return parent_group.sub_group_counts
    if isinstance(member_obj, EdgeDevice):
        return parent_group.edge_device_counts
    raise ValueError(
        f"Object of type {type(member_obj).__name__} cannot be linked into an edge device group.")
