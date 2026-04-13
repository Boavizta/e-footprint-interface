"""Unit tests for EdgeDeviceGroupWeb entity."""
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup

from model_builder.domain.entities.web_core.hardware.edge.edge_device_group_web import EdgeDeviceGroupWeb


class TestEdgeDeviceGroupWeb:
    """Tests for EdgeDeviceGroupWeb-specific behavior."""

    # --- get_creation_prerequisites ---

    def test_get_creation_prerequisites_returns_raw_available_groups_and_devices(self, minimal_model_web):
        parent = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Building"))
        device = minimal_model_web.add_new_efootprint_object_to_system(
            EdgeDevice.from_defaults("Sensor", components=[]))

        prerequisites = EdgeDeviceGroupWeb.get_creation_prerequisites(minimal_model_web)

        assert [group.efootprint_id for group in prerequisites["available_edge_device_groups"]] == [parent.efootprint_id]
        assert [edge_device.efootprint_id for edge_device in prerequisites["available_edge_devices"]] == [device.efootprint_id]

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
