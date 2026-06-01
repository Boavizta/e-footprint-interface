"""Tests for calculus graph visualization of calculated attributes.

These tests verify that calculated attributes can be visualized as dependency graphs
showing how values are computed from their ancestors.
"""
import pytest
from playwright.sync_api import expect

from tests.e2e.pages import ModelBuilderPage


def _open_calculus_graph_frame(page, graph_url, retries=3):
    """Navigate to a calculus-graph page and return the iframe's content frame.

    The graph HTML is handed off from `display_calculus_graph` to the iframe's
    `get_calculus_graph` request through the (Postgres-only) DB cache. Under the parallel
    e2e harness on SQLite, that single write is occasionally dropped under DB-lock
    contention, so the iframe shows "Graph content expired". Re-navigating the parent URL
    mints a fresh cache key and re-writes, so we retry the parent request rather than
    reloading the single-use iframe URL. This is a local/CI SQLite artifact, not a
    production bug (Postgres handles concurrent writes). See specs/testing.md.
    """
    for _ in range(retries):
        page.goto(graph_url)
        iframe = page.locator("iframe")
        expect(iframe).to_be_attached()
        frame = iframe.element_handle().content_frame()
        assert frame is not None
        expect(frame.locator("body")).not_to_be_empty()
        if "Graph content expired" not in frame.locator("body").inner_text():
            return frame
    return frame


@pytest.mark.e2e
class TestCalculusGraph:
    """Tests for calculus graph visualization."""

    def test_simple_calculus_graph_opens(self, minimal_complete_model_builder: ModelBuilderPage):
        """Calculus graph should open and render for simple calculated attributes.

        Verifies:
        - Navigation to usage journey calculated attributes works
        - Calculus graph link exists for duration attribute
        - Graph page loads with iframe containing vis.js network visualization
        """
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        uj_card = model_builder.get_object_card("UsageJourney", "Test Journey")
        uj_card.click_edit_button()

        # Expand calculated attributes section
        calc_attrs_toggle = page.locator("button[data-bs-target='#collapseCalculatedAttributesUsageJourney']")
        expect(calc_attrs_toggle).to_be_visible()
        calc_attrs_toggle.click()

        # Expand duration attribute
        duration_toggle = page.locator("button[data-bs-target='#collapse-calculated_attributes-duration']")
        expect(duration_toggle).to_be_enabled()
        duration_toggle.click()

        # Navigate to calculus graph
        graph_link = page.locator("a[href*='/model_builder/display-calculus-graph/']").first
        expect(graph_link).to_be_visible()
        graph_url = graph_link.get_attribute("href")
        assert graph_url is not None

        # Verify iframe with vis.js network
        frame = _open_calculus_graph_frame(page, graph_url)
        expect(frame.locator("#mynetwork")).to_be_attached()
        expect(frame.locator("script[type='text/javascript']").first).to_be_attached()

    def test_by_usage_pattern_calculus_graph_opens(self, minimal_complete_model_builder: ModelBuilderPage):
        """Calculus graph should work for per-usage-pattern calculated attributes.

        Verifies:
        - Navigation to per-pattern attributes (hourly_occurrences_per_usage_pattern)
        - Can select usage pattern's graph
        - Graph renders correctly
        """
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Expand UsageJourneyStep accordion
        ujs_card = model_builder.get_object_card("UsageJourneyStep", "Test Step")
        ujs_card.open_accordion()

        # Open job form
        job_card = model_builder.get_object_card("Job", "Test Job")
        job_card.click_edit_button()

        # Expand calculated attributes
        calc_attrs_toggle = page.locator(
            "button[data-bs-target^='#collapseCalculatedAttributesJob']")
        expect(calc_attrs_toggle).to_be_visible()
        calc_attrs_toggle.click()

        # Expand hourly_occurrences_per_usage_pattern group
        occurrences_toggle = page.locator(
            "button[data-bs-target^='#collapse-calculated_attributes_hourly_occurrences_per_usage_pattern']"
        )
        expect(occurrences_toggle).to_be_enabled()
        occurrences_toggle.click()

        # Find calculus graph link
        graph_link = page.locator(
            "a[href*='/model_builder/display-calculus-graph/'][href*='hourly_occurrences_per_usage_pattern']").first

        # Navigate to graph
        graph_url = graph_link.get_attribute("href")
        assert graph_url is not None

        # Verify iframe with vis.js network
        frame = _open_calculus_graph_frame(page, graph_url)
        expect(frame.locator("#mynetwork")).to_be_attached()
        expect(frame.locator("script[type='text/javascript']").first).to_be_attached()
