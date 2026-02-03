"""Unit tests for ServiceWeb entity."""
from types import SimpleNamespace

from model_builder.domain.entities.web_builders.services.service_web import ServiceWeb
from tests.unit_tests.domain.entities.snapshot_utils import assert_creation_context_matches_snapshot
from tests.unit_tests.domain.entities.snapshot_model_webs import build_service_model_web


class TestServiceWeb:
    """Tests for ServiceWeb-specific behavior."""

    # --- get_htmx_form_config ---

    def test_get_htmx_form_config_targets_parent_server(self):
        """HTMX config should link to the server and insert before the add button."""
        server = SimpleNamespace(web_id="server-1")
        context_data = {
            "server": server,
            "efootprint_id_of_parent_to_link_to": "server-id",
        }

        assert ServiceWeb.get_htmx_form_config(context_data) == {
            "hx_vals": {"efootprint_id_of_parent_to_link_to": "server-id"},
            "hx_target": "#add-service-to-server-1",
            "hx_swap": "beforebegin",
        }

    # --- prepare_creation_input ---

    def test_prepare_creation_input_maps_parent_id_to_server(self):
        """Creation input should map parent id to server field without mutating input."""
        form_data = {"efootprint_id_of_parent_to_link_to": "server-id"}

        result = ServiceWeb.prepare_creation_input(form_data)

        assert result["server"] == "server-id"
        assert "server" not in form_data

    # --- generate_object_creation_context (snapshot test) ---

    def test_generate_object_creation_context_matches_snapshot(self):
        """Creation context form structure matches reference snapshot."""
        model_web = build_service_model_web()
        assert_creation_context_matches_snapshot(ServiceWeb, model_web=model_web, object_type="Service")
