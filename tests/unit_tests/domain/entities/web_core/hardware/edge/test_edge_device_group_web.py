"""Unit tests for EdgeDeviceGroupWeb entity."""
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup

from model_builder.domain.entities.web_core.hardware.edge.edge_device_group_web import EdgeDeviceGroupWeb


class TestEdgeDeviceGroupWeb:
    """Tests for EdgeDeviceGroupWeb-specific behavior."""

    # --- prepare_creation_input ---

    def test_prepare_creation_input_adds_empty_group_dicts(self):
        """Creation input should add empty dict attributes without mutating input."""
        form_data = {"name": "Campus"}

        result = EdgeDeviceGroupWeb.prepare_creation_input(form_data)

        assert result["sub_group_counts"] == {}
        assert result["edge_device_counts"] == {}
        assert "sub_group_counts" not in form_data
        assert "edge_device_counts" not in form_data

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
