"""Unit tests for EdgeDeviceBaseWeb entity."""
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup

from model_builder.domain.entities.web_core.hardware.edge.edge_device_base_web import EdgeDeviceBaseWeb
from tests.unit_tests.domain.entities.snapshot_utils import assert_creation_context_matches_snapshot


def _build_edge_snapshot_model_web():
    model_web = MagicMock()
    model_web.get_web_objects_from_efootprint_type.return_value = []
    model_web.get_efootprint_objects_from_efootprint_type.return_value = []
    model_web.get_web_object_from_efootprint_id.return_value = MagicMock()
    return model_web


class TestEdgeDeviceBaseWeb:
    """Tests for EdgeDeviceBaseWeb-specific behavior."""

    # --- generate_object_creation_context (snapshot test) ---

    def test_generate_object_creation_context_matches_snapshot(self):
        """Creation context form structure matches reference snapshot."""
        model_web = _build_edge_snapshot_model_web()
        assert_creation_context_matches_snapshot(EdgeDeviceBaseWeb, model_web=model_web)

    # --- dict_membership_sections ---

    def test_dict_membership_sections_lists_parent_groups_and_joinable_groups(self):
        device = EdgeDevice.from_defaults("Shared Sensor", components=[])
        alpha = EdgeDeviceGroup("Alpha")
        beta = EdgeDeviceGroup("Beta")
        empty = EdgeDeviceGroup("Empty")
        alpha.edge_device_counts[device] = SourceValue(2 * u.dimensionless)
        beta.edge_device_counts[device] = SourceValue(0.3 * u.dimensionless)

        model_web = MagicMock()
        model_web.flat_efootprint_objs_dict = {obj.id: obj for obj in (device, alpha, beta, empty)}
        web_obj = EdgeDeviceBaseWeb(device, model_web)

        assert web_obj.dict_membership_sections == [{
            "parent_class_name": "EdgeDeviceGroup",
            "attr_name": "edge_device_counts",
            "memberships": [
                {"parent_id": alpha.id, "parent_name": "Alpha", "count": 2.0},
                {"parent_id": beta.id, "parent_name": "Beta", "count": 0.3},
            ],
            "available_parents": [{"efootprint_id": empty.id, "name": "Empty"}],
        }]
