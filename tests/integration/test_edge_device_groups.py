from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u

from model_builder.domain.entities.web_core.model_web import ModelWeb
from tests.fixtures.form_data_builders import create_post_data_from_class_default_values
from tests.fixtures.use_case_helpers import create_object, delete_object


def _model_web(repository) -> ModelWeb:
    return ModelWeb(repository)


def _link_group_to_group(repository, parent_id: str, child_id: str, count: int = 1) -> None:
    model_web = _model_web(repository)
    parent_group = model_web.get_efootprint_object_from_efootprint_id(parent_id, "EdgeDeviceGroup")
    child_group = model_web.get_efootprint_object_from_efootprint_id(child_id, "EdgeDeviceGroup")
    parent_group.sub_group_counts[child_group] = SourceValue(count * u.dimensionless)
    model_web.persist_to_cache()


def _set_group_device_count(repository, group_id: str, device_id: str, count: int) -> None:
    model_web = _model_web(repository)
    group = model_web.get_efootprint_object_from_efootprint_id(group_id, "EdgeDeviceGroup")
    device = model_web.get_efootprint_object_from_efootprint_id(device_id, "EdgeDevice")
    group.edge_device_counts[device] = SourceValue(count * u.dimensionless)
    model_web.persist_to_cache()


def _unlink_group_device(repository, group_id: str, device_id: str) -> None:
    model_web = _model_web(repository)
    group = model_web.get_efootprint_object_from_efootprint_id(group_id, "EdgeDeviceGroup")
    device = model_web.get_efootprint_object_from_efootprint_id(device_id, "EdgeDevice")
    del group.edge_device_counts[device]
    model_web.persist_to_cache()


def test_deleting_parent_group_promotes_child_groups_back_to_root_groups(default_system_repository):
    parent_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Building", "EdgeDeviceGroup"),
    )
    child_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Floor", "EdgeDeviceGroup"),
    )
    _link_group_to_group(default_system_repository, parent_id, child_id, count=2)

    delete_object(default_system_repository, parent_id)

    model_web = _model_web(default_system_repository)
    assert parent_id not in model_web.flat_efootprint_objs_dict
    assert [group.efootprint_id for group in model_web.root_edge_device_groups] == [child_id]


def test_deleting_grouped_edge_device_removes_all_parent_memberships(default_system_repository):
    device_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Shared Sensor", "EdgeDevice", components=""),
    )
    alpha_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Alpha", "EdgeDeviceGroup"),
    )
    beta_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Beta", "EdgeDeviceGroup"),
    )
    _set_group_device_count(default_system_repository, alpha_id, device_id, count=2)
    _set_group_device_count(default_system_repository, beta_id, device_id, count=4)

    delete_object(default_system_repository, device_id)

    model_web = _model_web(default_system_repository)
    alpha = model_web.get_efootprint_object_from_efootprint_id(alpha_id, "EdgeDeviceGroup")
    beta = model_web.get_efootprint_object_from_efootprint_id(beta_id, "EdgeDeviceGroup")
    assert device_id not in model_web.flat_efootprint_objs_dict
    assert alpha.edge_device_counts == {}
    assert beta.edge_device_counts == {}


def test_updating_one_membership_count_preserves_other_group_memberships(default_system_repository):
    device_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Shared Sensor", "EdgeDevice", components=""),
    )
    alpha_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Alpha", "EdgeDeviceGroup"),
    )
    beta_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Beta", "EdgeDeviceGroup"),
    )
    _set_group_device_count(default_system_repository, alpha_id, device_id, count=1)
    _set_group_device_count(default_system_repository, beta_id, device_id, count=3)

    _set_group_device_count(default_system_repository, alpha_id, device_id, count=5)

    model_web = _model_web(default_system_repository)
    device = model_web.get_efootprint_object_from_efootprint_id(device_id, "EdgeDevice")
    alpha = model_web.get_efootprint_object_from_efootprint_id(alpha_id, "EdgeDeviceGroup")
    beta = model_web.get_efootprint_object_from_efootprint_id(beta_id, "EdgeDeviceGroup")
    assert alpha.edge_device_counts[device].value.magnitude == 5
    assert beta.edge_device_counts[device].value.magnitude == 3


def test_unlinking_device_from_multiple_groups_only_ungroups_after_last_membership(default_system_repository):
    device_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Shared Sensor", "EdgeDevice", components=""),
    )
    alpha_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Alpha", "EdgeDeviceGroup"),
    )
    beta_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Beta", "EdgeDeviceGroup"),
    )
    _set_group_device_count(default_system_repository, alpha_id, device_id, count=1)
    _set_group_device_count(default_system_repository, beta_id, device_id, count=2)

    _unlink_group_device(default_system_repository, alpha_id, device_id)
    model_web = _model_web(default_system_repository)
    assert [device.efootprint_id for device in model_web.ungrouped_edge_devices] == []

    _unlink_group_device(default_system_repository, beta_id, device_id)
    model_web = _model_web(default_system_repository)
    assert [device.efootprint_id for device in model_web.ungrouped_edge_devices] == [device_id]
