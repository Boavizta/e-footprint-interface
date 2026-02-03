"""Unit tests for JourneyStepBaseWeb entity."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from model_builder.domain.entities.web_core.usage.journey_step_base_web import JourneyStepBaseWeb
from tests.unit_tests.domain.entities.snapshot_utils import assert_creation_context_matches_snapshot
from tests.unit_tests.domain.entities.web_core.usage.snapshot_model_webs import build_basic_model_web


class TestJourneyStepBaseWeb:
    """Tests for JourneyStepBaseWeb-specific behavior."""

    # --- get_htmx_form_config ---

    def test_get_htmx_form_config_links_to_parent(self):
        """HTMX config should include parent link and swap none."""
        context_data = {"efootprint_id_of_parent_to_link_to": "parent-id"}
        assert JourneyStepBaseWeb.get_htmx_form_config(context_data) == {
            "hx_vals": {"efootprint_id_of_parent_to_link_to": "parent-id"},
            "hx_swap": "none",
        }

    # --- icon helpers ---

    def test_icon_links_and_styles_follow_step_order(self):
        """Icon links and leaderline styles should point to the next step or add button."""
        model_web = MagicMock()
        list_container = SimpleNamespace(web_id="journey-1", accordion_children=[])

        step1_obj = SimpleNamespace(id="step1", class_as_simple_str="UsageJourneyStep", name="step1")
        step2_obj = SimpleNamespace(id="step2", class_as_simple_str="UsageJourneyStep", name="step2")

        step1 = JourneyStepBaseWeb(step1_obj, model_web, list_container=list_container)
        step2 = JourneyStepBaseWeb(step2_obj, model_web, list_container=list_container)
        list_container.accordion_children = [step1, step2]

        assert step1.icon_links_to == f"icon-{step2.web_id}"
        assert step1.icon_leaderline_style == "vertical-step-swimlane"
        assert step2.icon_links_to == f"icon-add-step-to-{list_container.web_id}"
        assert step2.icon_leaderline_style == "step-dot-line"

        data_attrs = step1.data_attributes_as_list_of_dict
        assert data_attrs[-1] == {
            "id": f"icon-{step1.web_id}",
            "data-link-to": step1.icon_links_to,
            "data-line-opt": step1.icon_leaderline_style,
        }

    # --- generate_object_creation_context (snapshot test) ---

    def test_generate_object_creation_context_matches_snapshot(self):
        """Creation context form structure matches reference snapshot."""
        model_web = build_basic_model_web()
        assert_creation_context_matches_snapshot(JourneyStepBaseWeb, model_web=model_web, object_type="UsageJourneyStep")
