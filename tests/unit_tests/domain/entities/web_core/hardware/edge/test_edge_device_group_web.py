"""Unit tests for EdgeDeviceGroupWeb entity."""
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup

from model_builder.domain.entities.web_core.hardware.edge.edge_device_group_web import EdgeDeviceGroupWeb


class TestEdgeDeviceGroupWeb:
    """Tests for EdgeDeviceGroupWeb-specific behavior."""

    # --- group entry helpers ---

    def test_sub_group_entries_wrap_children_and_keep_counts(self):
        """Sub-group entries should expose wrapped children with their counts."""
        model_web = MagicMock()
        parent = EdgeDeviceGroup("Building")
        child = EdgeDeviceGroup("Floor")
        parent.sub_group_counts[child] = SourceValue(2 * u.dimensionless)
        web_obj = EdgeDeviceGroupWeb(parent, model_web)

        entries = web_obj.sub_group_entries

        assert len(entries) == 1
        assert entries[0]["object"].name == "Floor"
        assert entries[0]["object"].dict_container == web_obj
        assert entries[0]["object"].accordion_parent == web_obj
        assert entries[0]["count"] == 2

    def test_edge_device_entries_wrap_devices_and_keep_counts(self):
        """Device entries should expose wrapped children with their counts."""
        model_web = MagicMock()
        group = EdgeDeviceGroup("Building")
        device = EdgeDevice("Sensor", SourceValue(50 * u.kg), [], SourceValue(6 * u.year))
        group.edge_device_counts[device] = SourceValue(3 * u.dimensionless)
        web_obj = EdgeDeviceGroupWeb(group, model_web)

        entries = web_obj.edge_device_entries

        assert len(entries) == 1
        assert entries[0]["object"].name == "Sensor"
        assert entries[0]["object"].dict_container == web_obj
        assert entries[0]["object"].accordion_parent == web_obj
        assert entries[0]["count"] == 3

    # --- filter_dict_count_options ---

    def test_filter_dict_count_options_excludes_self_and_ancestors_for_sub_groups(self, minimal_model_web):
        campus = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Campus"))
        building = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Building"))
        floor = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Floor"))
        room = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Room"))
        annex = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Annex"))

        campus.modeling_obj.sub_group_counts[building.modeling_obj] = SourceValue(1 * u.dimensionless)
        building.modeling_obj.sub_group_counts[floor.modeling_obj] = SourceValue(1 * u.dimensionless)
        floor.modeling_obj.sub_group_counts[room.modeling_obj] = SourceValue(2 * u.dimensionless)

        filtered = floor.filter_dict_count_options("sub_group_counts", minimal_model_web.edge_device_groups)

        assert sorted(group.efootprint_id for group in filtered) == sorted(
            [annex.efootprint_id, room.efootprint_id])

    def test_filter_dict_count_options_for_edge_devices_only_excludes_self(self, minimal_model_web):
        group = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Group"))
        shared_device = minimal_model_web.add_new_efootprint_object_to_system(
            EdgeDevice.from_defaults("Shared Sensor", components=[]))
        free_device = minimal_model_web.add_new_efootprint_object_to_system(
            EdgeDevice.from_defaults("Free Sensor", components=[]))

        filtered = group.filter_dict_count_options("edge_device_counts", minimal_model_web.edge_devices)

        assert sorted(device.efootprint_id for device in filtered) == sorted(
            [free_device.efootprint_id, shared_device.efootprint_id])

    # --- pre_delete ---

    def test_pre_delete_removes_group_from_parent_group_dicts(self):
        """Deleting a group should unlink it from all parent group dicts first."""
        parent = EdgeDeviceGroup("Building")
        child = EdgeDeviceGroup("Floor")
        parent.sub_group_counts[child] = SourceValue(2 * u.dimensionless)
        web_obj = EdgeDeviceGroupWeb(child, MagicMock())

        EdgeDeviceGroupWeb.pre_delete(web_obj, MagicMock())

        assert child not in parent.sub_group_counts
        assert child.explainable_object_dicts_containers == []
