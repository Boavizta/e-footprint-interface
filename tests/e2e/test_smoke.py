"""Smoke tests to verify E2E test infrastructure works."""
import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
class TestSmoke:
    """Basic smoke tests to verify Playwright + Django integration."""

    def test_home_page_loads(self, model_builder_page):
        """Verify the home page loads and has the start button."""
        model_builder_page.page.goto("/")
        expect(model_builder_page.page.locator("#btn-start-modeling-my-service")).to_be_visible()

    def test_model_builder_loads_from_home(self, empty_model_builder):
        """Verify navigating from home to model builder works."""
        expect(empty_model_builder.canvas).to_be_visible()

    def test_model_builder_has_leader_line(self, empty_model_builder):
        """Verify LeaderLine JS library is loaded."""
        empty_model_builder.should_have_leader_line()

    def test_can_load_minimal_system(self, minimal_system_in_browser):
        """Verify loading a programmatically-created system works."""
        # The minimal system has a server named "Test Server"
        minimal_system_in_browser.object_should_exist("Server", "Test Server")

    def test_can_load_cypress_fixture(self, cypress_standard_model):
        """Verify loading existing Cypress fixtures works."""
        # The standard fixture has "My first usage journey"
        cypress_standard_model.object_should_exist("UsageJourney", "My first usage journey")
