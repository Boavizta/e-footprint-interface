"""Unit tests for EdgeDeviceWeb entity."""
from unittest.mock import MagicMock

from model_builder.domain.entities.web_core.hardware.edge.edge_device_web import EdgeDeviceWeb
from tests.unit_tests.domain.entities.snapshot_utils import assert_creation_context_matches_snapshot


def _build_edge_snapshot_model_web():
    model_web = MagicMock()
    model_web.get_web_objects_from_efootprint_type.return_value = []
    model_web.get_efootprint_objects_from_efootprint_type.return_value = []
    model_web.get_web_object_from_efootprint_id.return_value = MagicMock()
    return model_web


class TestEdgeDeviceWeb:
    """Tests for EdgeDeviceWeb-specific behavior."""

    # --- prepare_creation_input ---

    def test_prepare_creation_input_adds_components_list(self):
        """Creation input should add an empty components list without mutating input."""
        form_data = {"name": "Edge device"}

        result = EdgeDeviceWeb.prepare_creation_input(form_data)

        assert result["components"] == []
        assert "components" not in form_data

    # --- generate_object_creation_context (snapshot test) ---

    def test_generate_object_creation_context_matches_snapshot(self):
        """Creation context form structure matches reference snapshot."""
        model_web = _build_edge_snapshot_model_web()
        assert_creation_context_matches_snapshot(EdgeDeviceWeb, model_web=model_web, object_type="EdgeDeviceBase")
