"""Integration tests for edge device group membership invariants."""
import json

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup

from model_builder.domain.entities.web_core.model_web import ModelWeb
from tests.fixtures.form_data_builders import create_post_data_from_class_default_values
from tests.fixtures.use_case_helpers import create_object, delete_object


def _persist_dict_mutation(repository, parent_id: str, key_id: str, count: int | None) -> None:
    model_web = ModelWeb(repository)
    parent_group = model_web.get_efootprint_object_from_efootprint_id(parent_id, "EdgeDeviceGroup")
    key_obj = model_web.flat_efootprint_objs_dict[key_id]
    target_dict = parent_group.sub_group_counts if isinstance(key_obj, EdgeDeviceGroup) else parent_group.edge_device_counts

    if count is None:
        del target_dict[key_obj]
    else:
        target_dict[key_obj] = SourceValue(count * u.dimensionless)

    model_web.persist_to_cache()


def test_link_and_unlink_edge_device_updates_ungrouped_devices(default_system_repository):
    device_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Sensor", "EdgeDevice", components=""),
    )
    group_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Rack A", "EdgeDeviceGroup"),
    )

    _persist_dict_mutation(default_system_repository, group_id, device_id, count=1)

    model_web = ModelWeb(default_system_repository)
    assert [device.efootprint_id for device in model_web.ungrouped_edge_devices] == []

    _persist_dict_mutation(default_system_repository, group_id, device_id, count=None)

    model_web = ModelWeb(default_system_repository)
    assert [device.efootprint_id for device in model_web.ungrouped_edge_devices] == [device_id]


def test_link_and_unlink_sub_group_updates_root_groups(default_system_repository):
    parent_group_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Building", "EdgeDeviceGroup"),
    )
    child_group_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Floor", "EdgeDeviceGroup"),
    )

    _persist_dict_mutation(default_system_repository, parent_group_id, child_group_id, count=2)

    model_web = ModelWeb(default_system_repository)
    assert [group.efootprint_id for group in model_web.root_edge_device_groups] == [parent_group_id]

    _persist_dict_mutation(default_system_repository, parent_group_id, child_group_id, count=None)

    model_web = ModelWeb(default_system_repository)
    assert {group.efootprint_id for group in model_web.root_edge_device_groups} == {parent_group_id, child_group_id}


def test_delete_grouped_edge_device_removes_parent_group_reference(default_system_repository):
    device_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Sensor", "EdgeDevice", components=""),
    )
    group_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Rack A", "EdgeDeviceGroup"),
    )
    _persist_dict_mutation(default_system_repository, group_id, device_id, count=3)

    delete_object(default_system_repository, device_id)

    model_web = ModelWeb(default_system_repository)
    group = model_web.get_efootprint_object_from_efootprint_id(group_id, "EdgeDeviceGroup")
    assert "EdgeDevice" not in default_system_repository.get_system_data()
    assert len(group.edge_device_counts) == 0


def test_delete_nested_group_promotes_child_group_back_to_root(default_system_repository):
    parent_group_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Building", "EdgeDeviceGroup"),
    )
    child_group_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Floor", "EdgeDeviceGroup"),
    )
    grandchild_group_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Shelf", "EdgeDeviceGroup"),
    )
    _persist_dict_mutation(default_system_repository, parent_group_id, child_group_id, count=1)
    _persist_dict_mutation(default_system_repository, child_group_id, grandchild_group_id, count=1)

    delete_object(default_system_repository, child_group_id)

    model_web = ModelWeb(default_system_repository)
    assert {group.efootprint_id for group in model_web.root_edge_device_groups} == {
        parent_group_id,
        grandchild_group_id,
    }


def test_create_group_with_initial_sub_groups_and_devices(default_system_repository):
    first_device_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Sensor A", "EdgeDevice", components=""),
    )
    second_device_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Sensor B", "EdgeDevice", components=""),
    )
    child_group_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Floor", "EdgeDeviceGroup"),
    )

    parent_group_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Building",
            "EdgeDeviceGroup",
            sub_group_counts=json.dumps({child_group_id: 2}),
            edge_device_counts=json.dumps({first_device_id: 3, second_device_id: 1}),
        ),
    )

    model_web = ModelWeb(default_system_repository)
    parent_group = model_web.get_efootprint_object_from_efootprint_id(parent_group_id, "EdgeDeviceGroup")

    assert {
        group.efootprint_id: parent_group.sub_group_counts[group.modeling_obj].value.magnitude
        for group in model_web.edge_device_groups
        if group.modeling_obj in parent_group.sub_group_counts
    } == {child_group_id: 2}
    assert {
        device.efootprint_id: parent_group.edge_device_counts[device.modeling_obj].value.magnitude
        for device in model_web.edge_devices
        if device.modeling_obj in parent_group.edge_device_counts
    } == {first_device_id: 3, second_device_id: 1}
    assert [device.efootprint_id for device in model_web.ungrouped_edge_devices] == []
    assert [group.efootprint_id for group in model_web.root_edge_device_groups] == [parent_group_id]
