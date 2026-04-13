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

    # --- get_edition_context_overrides ---

    def test_get_edition_context_overrides_returns_group_memberships(self):
        device = EdgeDevice.from_defaults("Shared Sensor", components=[])
        alpha = EdgeDeviceGroup("Alpha")
        beta = EdgeDeviceGroup("Beta")
        alpha.edge_device_counts[device] = SourceValue(2 * u.dimensionless)
        beta.edge_device_counts[device] = SourceValue(5 * u.dimensionless)

        web_obj = EdgeDeviceBaseWeb(device, MagicMock())

        assert web_obj.get_edition_context_overrides() == {
            "group_memberships": [
                {"group_id": alpha.id, "group_name": "Alpha", "count": 2.0},
                {"group_id": beta.id, "group_name": "Beta", "count": 5.0},
            ]
        }
