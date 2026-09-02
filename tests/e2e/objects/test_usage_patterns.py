"""Tests for usage pattern creation with timeseries configuration."""
import pytest
from playwright.sync_api import expect

from tests.e2e.pages import ModelBuilderPage


@pytest.mark.e2e
class TestUsagePatterns:
    """Tests for usage pattern CRUD operations."""

    def test_create_usage_pattern_with_timeseries(self, minimal_complete_model_builder: ModelBuilderPage):
        """Test creating a usage pattern with full timeseries configuration.

        Uses complete system fixture that has UJ, steps, server, service, job.
        """
        model_builder = minimal_complete_model_builder
        side_panel = model_builder.side_panel
        page = model_builder.page

        up_name = "New Usage Pattern"
        model_builder.click_add_usage_pattern()
        side_panel.fill_field("UsagePattern_name", up_name)

        # Set modeling duration
        page.locator("#UsagePattern_hourly_occurrences__modeling_duration_value").fill("2")
        page.locator("#UsagePattern_hourly_occurrences__modeling_duration_value").dispatch_event("change")

        # Chart should be hidden until volume is set
        expect(page.locator("#chartTimeseries")).to_contain_class("d-none")

        # Set initial volume - chart should appear
        page.locator("#UsagePattern_hourly_occurrences__initial_volume").fill("1000")
        expect(page.locator("#chartTimeseries")).not_to_have_class("d-none")

        # Clear volume - chart should hide again
        page.locator("#UsagePattern_hourly_occurrences__initial_volume").fill("")
        page.locator("#UsagePattern_hourly_occurrences__initial_volume").dispatch_event("change")
        expect(page.locator("#chartTimeseries")).to_contain_class("d-none")

        page.locator("#UsagePattern_hourly_occurrences__initial_volume").fill("1000")

        # Set growth rate
        page.locator("#UsagePattern_hourly_occurrences__net_growth_rate_in_percentage").fill("25")
        page.locator("#UsagePattern_hourly_occurrences__net_growth_rate_in_percentage").dispatch_event("change")
        side_panel.select_option("UsagePattern_hourly_occurrences__net_growth_rate_timespan", "year")

        # The first available journey is selected by default.
        side_panel.submit_and_wait_for_close()

        model_builder.object_should_exist("UsagePattern", up_name)

    def test_weighted_multiple_journeys_persist_and_keep_one_required(
        self, minimal_complete_model_builder: ModelBuilderPage
    ):
        model_builder = minimal_complete_model_builder
        side_panel = model_builder.side_panel
        page = model_builder.page

        model_builder.click_add_usage_journey()
        side_panel.fill_field("UsageJourney_name", "Second Journey")
        side_panel.submit_and_wait_for_close()

        model_builder.click_add_usage_pattern()
        side_panel.fill_field("UsagePattern_name", "Weighted Journeys")
        side_panel.fill_field("UsagePattern_hourly_occurrences__initial_volume", "1")
        side_panel.add_to_dict_count("UsagePattern_usage_journeys", "Second Journey", count="2.5")

        rows = page.locator("#objects-already-selected-for-UsagePattern_usage_journeys tr")
        expect(rows).to_have_count(2)
        side_panel.remove_from_dict_count("UsagePattern_usage_journeys", "Test Journey")
        expect(rows).to_have_count(1)
        expect(rows.locator("button")).to_be_disabled()
        side_panel.submit_and_wait_for_close()

        model_builder.get_object_card("UsagePattern", "Weighted Journeys").click_edit_button()
        persisted = page.locator(
            "#objects-already-selected-for-UsagePattern_usage_journeys tr"
        ).filter(has_text="Second Journey")
        expect(persisted.locator("input[type='number']")).to_have_value("2.5")
