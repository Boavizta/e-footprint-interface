"""Tests for form behavior - unsaved changes, advanced options, source labels."""
import pytest
from playwright.sync_api import expect

from tests.e2e.pages import ModelBuilderPage


@pytest.mark.e2e
class TestUnsavedChangesWarning:
    """Tests for the unsaved changes warning modal."""

    def test_warns_when_closing_panel_with_unsaved_changes(self, empty_model_builder: ModelBuilderPage):
        """User should be warned when closing a form with unsaved changes."""
        model_builder = empty_model_builder
        page = model_builder.page

        # Open form and make changes
        model_builder.click_add_usage_journey()
        page.locator("#UsageJourney_name").click()
        page.locator("#UsageJourney_name").type("test name")

        # Try to close panel
        page.locator("#btn-close-side-panel").click()

        # Warning modal should appear (wait for Bootstrap modal animation)
        expect(page.locator("#unsavedModal.show")).to_be_visible()

        # Cancel to stay on form
        page.locator("#cancel-unsaved-modal").click()
        expect(page.locator("#unsavedModal.show")).not_to_be_visible()

    def test_warns_when_opening_new_panel_with_unsaved_changes(self, empty_model_builder: ModelBuilderPage):
        """User should be warned when opening another form with unsaved changes."""
        model_builder = empty_model_builder
        page = model_builder.page

        # Open form and make changes
        model_builder.click_add_usage_journey()
        page.locator("#UsageJourney_name").click()
        page.locator("#UsageJourney_name").type("test name")

        # Try to open another form by clicking on existing UJ
        default_uj_card = model_builder.get_object_card("UsageJourney", "My first usage journey")
        default_uj_card.locator.locator("button[id^='button-']").first.click()

        # Warning modal should appear (wait for Bootstrap modal animation)
        expect(page.locator("#unsavedModal.show")).to_be_visible()

        # Cancel to stay on form
        page.locator("#cancel-unsaved-modal").click()
        expect(page.locator("#unsavedModal.show")).not_to_be_visible()


@pytest.mark.e2e
class TestAdvancedOptions:
    """Tests for the advanced options toggle in forms."""

    def test_server_advanced_options_toggle_and_persist(self, empty_model_builder: ModelBuilderPage):
        """Advanced options should toggle visibility and values should persist."""
        model_builder = empty_model_builder
        side_panel = model_builder.side_panel
        page = model_builder.page

        server_name = "Test Server"

        # Create server with advanced option modified
        model_builder.click_add_server()
        side_panel.select_object_type("Server")
        side_panel.fill_field("Server_name", server_name)
        side_panel.fill_field("Server_average_carbon_intensity", "700")

        # Advanced section should be hidden by default
        expect(page.locator("#advanced-Server")).not_to_be_visible()

        # Toggle advanced options
        page.locator("#display-advanced-Server").click()
        expect(page.locator("#advanced-Server")).to_be_visible()

        # Modify an advanced field
        page.locator("#Server_power").clear()
        page.locator("#Server_power").fill("888")

        # Toggle closed and submit
        page.locator("#display-advanced-Server").click()
        expect(page.locator("#advanced-Server")).not_to_be_visible()
        side_panel.submit_and_wait_for_close()

        # Re-open and verify values persisted
        server_card = model_builder.get_object_card("Server", server_name)
        server_card.click_edit_button()

        expect(page.locator("#Server_average_carbon_intensity")).to_have_value("700")
        expect(page.locator("#advanced-Server")).not_to_be_visible()

        page.locator("#display-advanced-Server").click()
        expect(page.locator("#advanced-Server")).to_be_visible()
        expect(page.locator("#Server_power")).to_have_value("888")


@pytest.mark.e2e
class TestSourceLabels:
    """Tests for source labels displayed in forms."""

    def test_source_labels_display_in_usage_pattern_form(self, empty_model_builder: ModelBuilderPage):
        """Source labels should display correctly when creating and editing."""
        model_builder = empty_model_builder
        side_panel = model_builder.side_panel
        page = model_builder.page

        # Create usage pattern
        model_builder.click_add_usage_pattern()
        page.locator("#UsagePattern_hourly_usage_journey_starts__modeling_duration_value").fill("2")
        page.locator("#UsagePattern_hourly_usage_journey_starts__initial_volume").fill("1000")

        # Source label should show "user data"
        expect(page.locator("#source-UsagePattern_hourly_usage_journey_starts")).to_contain_text("Source: user data")

        side_panel.submit_and_wait_for_close()

        # Re-open and verify source label persists
        up_card = model_builder.get_object_card("UsagePattern", "Usage pattern 1")
        up_card.click_edit_button()

        expect(page.locator("#source-UsagePattern_hourly_usage_journey_starts")).to_contain_text("Source: user data")

        # Modify and verify source still shows
        page.locator("#UsagePattern_hourly_usage_journey_starts__net_growth_rate_in_percentage").fill("5")
        expect(page.locator("#source-UsagePattern_hourly_usage_journey_starts")).to_contain_text("Source: user data")
