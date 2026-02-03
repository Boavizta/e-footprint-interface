"""Unit tests for EdgeDeviceBaseWeb entity."""
from unittest.mock import MagicMock

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
