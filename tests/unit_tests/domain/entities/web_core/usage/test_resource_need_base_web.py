"""Unit tests for ResourceNeedBaseWeb behavior."""
from model_builder.domain.entities.web_core.usage.resource_need_base_web import ResourceNeedBaseWeb


class TestResourceNeedBaseWeb:
    """Tests for ResourceNeedBaseWeb behavior."""

    # --- get_htmx_form_config ---

    def test_get_htmx_form_config_links_to_parent(self):
        """HTMX config should include parent link and swap none."""
        context_data = {"efootprint_id_of_parent_to_link_to": "parent-id"}

        assert ResourceNeedBaseWeb.get_htmx_form_config(context_data) == {
            "hx_vals": {"efootprint_id_of_parent_to_link_to": "parent-id"},
            "hx_swap": "none",
        }
