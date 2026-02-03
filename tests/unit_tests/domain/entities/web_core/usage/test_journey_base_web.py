"""Unit tests for JourneyBaseWeb entity."""
from model_builder.domain.entities.web_core.usage.journey_base_web import JourneyBaseWeb
from tests.unit_tests.domain.entities.snapshot_utils import assert_creation_context_matches_snapshot
from tests.unit_tests.domain.entities.snapshot_model_webs import build_basic_model_web


class TestJourneyBaseWeb:
    """Tests for JourneyBaseWeb-specific behavior."""

    # --- get_htmx_form_config ---

    def test_get_htmx_form_config_targets_journey_list(self):
        """HTMX config should append to the journey list."""
        assert JourneyBaseWeb.get_htmx_form_config({}) == {"hx_target": "#uj-list", "hx_swap": "beforeend"}

    # --- generate_object_creation_context (snapshot test) ---

    def test_generate_object_creation_context_matches_snapshot(self):
        """Creation context form structure matches reference snapshot."""
        model_web = build_basic_model_web()
        assert_creation_context_matches_snapshot(JourneyBaseWeb, model_web=model_web, object_type="UsageJourney")
