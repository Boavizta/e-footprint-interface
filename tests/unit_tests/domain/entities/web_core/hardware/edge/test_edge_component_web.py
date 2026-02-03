"""Unit tests for EdgeComponentWeb entity."""
from unittest.mock import MagicMock

from model_builder.domain.entities.web_core.hardware.edge.edge_component_base_web import EdgeComponentWeb
from tests.unit_tests.domain.entities.snapshot_utils import assert_creation_context_matches_snapshot


def _build_edge_component_snapshot_model_web():
    model_web = MagicMock()
    model_web.get_web_objects_from_efootprint_type.return_value = []
    model_web.get_efootprint_objects_from_efootprint_type.return_value = []
    model_web.get_web_object_from_efootprint_id.return_value = MagicMock()
    return model_web


class TestEdgeComponentWeb:
    """Tests for EdgeComponentWeb-specific behavior."""

    # --- get_htmx_form_config ---

    def test_get_htmx_form_config_includes_parent_id(self):
        """HTMX config should include the parent ID for linking."""
        context_data = {"efootprint_id_of_parent_to_link_to": "parent-id"}

        config = EdgeComponentWeb.get_htmx_form_config(context_data)

        assert config == {"hx_vals": {"efootprint_id_of_parent_to_link_to": "parent-id"}}

    # --- generate_object_creation_context (snapshot test) ---

    def test_generate_object_creation_context_matches_snapshot(self):
        """Creation context form structure matches reference snapshot."""
        model_web = _build_edge_component_snapshot_model_web()
        assert_creation_context_matches_snapshot(EdgeComponentWeb, model_web=model_web)
