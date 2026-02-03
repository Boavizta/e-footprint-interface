"""Unit tests for RecurrentEdgeComponentNeedWeb entity."""
from unittest.mock import MagicMock

import pytest

from model_builder.domain.entities.web_core.usage.edge.recurrent_edge_component_need_web import (
    RecurrentEdgeComponentNeedWeb,
)
from tests.unit_tests.domain.entities.snapshot_utils import assert_creation_context_matches_snapshot
from tests.unit_tests.domain.entities.snapshot_model_webs import build_recurrent_edge_component_need_model_web


class TestRecurrentEdgeComponentNeedWeb:
    """Tests for RecurrentEdgeComponentNeedWeb-specific behavior."""

    # --- get_form_creation_data ---

    def test_get_form_creation_data_maps_bit_ram_to_gb_ram(self):
        """Compatible unit bit_ram should map to GB_ram in dynamic data."""
        model_web = MagicMock()
        recurrent_need = MagicMock()
        edge_device = MagicMock()
        component = MagicMock()
        component.name = "Component"
        component.efootprint_id = "component-id"
        component.get_efootprint_value.return_value = ["bit_ram"]
        edge_device.components = [component]
        recurrent_need.edge_device = edge_device
        model_web.get_web_object_from_efootprint_id.return_value = recurrent_need

        data = RecurrentEdgeComponentNeedWeb.get_form_creation_data(model_web, "parent-id")

        assert data["extra_dynamic_data"]["component_units_mapping"]["component-id"] == "GB_ram"

    def test_get_form_creation_data_requires_components(self):
        """Missing components should raise an explicit error."""
        model_web = MagicMock()
        recurrent_need = MagicMock()
        edge_device = MagicMock()
        edge_device.components = []
        recurrent_need.edge_device = edge_device
        model_web.get_web_object_from_efootprint_id.return_value = recurrent_need

        with pytest.raises(ValueError):
            RecurrentEdgeComponentNeedWeb.get_form_creation_data(model_web, "parent-id")

    # --- get_htmx_form_config ---

    def test_get_htmx_form_config_includes_parent_id(self):
        """HTMX config should include the parent ID for linking."""
        context_data = {"efootprint_id_of_parent_to_link_to": "parent-id"}

        assert RecurrentEdgeComponentNeedWeb.get_htmx_form_config(context_data) == {
            "hx_vals": {"efootprint_id_of_parent_to_link_to": "parent-id"}
        }

    # --- generate_object_creation_context (snapshot test) ---

    def test_generate_object_creation_context_matches_snapshot(self):
        """Creation context form structure matches reference snapshot."""
        model_web = build_recurrent_edge_component_need_model_web()
        assert_creation_context_matches_snapshot(RecurrentEdgeComponentNeedWeb, model_web=model_web)
