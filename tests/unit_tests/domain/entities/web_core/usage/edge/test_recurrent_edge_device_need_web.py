"""Unit tests for RecurrentEdgeDeviceNeedWeb entity."""
from model_builder.domain.entities.web_core.usage.edge.recurrent_edge_device_need_web import RecurrentEdgeDeviceNeedWeb
from tests.unit_tests.domain.entities.snapshot_utils import assert_creation_context_matches_snapshot
from tests.unit_tests.domain.entities.snapshot_model_webs import build_recurrent_edge_device_need_model_web


class TestRecurrentEdgeDeviceNeedWeb:
    """Tests for RecurrentEdgeDeviceNeedWeb-specific behavior."""

    # --- prepare_creation_input ---

    def test_prepare_creation_input_adds_component_needs_list(self):
        """Creation input should add an empty recurrent_edge_component_needs list without mutating input."""
        form_data = {"name": "Need"}

        result = RecurrentEdgeDeviceNeedWeb.prepare_creation_input(form_data)

        assert result["recurrent_edge_component_needs"] == []
        assert "recurrent_edge_component_needs" not in form_data

    # --- generate_object_creation_context (snapshot test) ---

    def test_generate_object_creation_context_matches_snapshot(self):
        """Creation context form structure matches reference snapshot."""
        model_web = build_recurrent_edge_device_need_model_web()
        assert_creation_context_matches_snapshot(RecurrentEdgeDeviceNeedWeb, model_web=model_web)
