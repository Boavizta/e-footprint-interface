"""Tests for usage pattern creation with timeseries configuration."""
import pytest
from playwright.sync_api import expect

from efootprint.api_utils.system_to_json import system_to_json

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage
from tests.fixtures import build_minimal_system


@pytest.fixture
def system_dict_complete():
    """Create a complete system dict with all objects connected."""
    system = build_minimal_system("Test System")
    return system_to_json(system, save_calculated_attributes=True)


@pytest.fixture
def complete_system_in_browser(model_builder_page: ModelBuilderPage, system_dict_complete):
    """Load complete system into browser."""
    return load_system_dict_into_browser(model_builder_page, system_dict_complete)


@pytest.mark.e2e
class TestUsagePatterns:
    """Tests for usage pattern CRUD operations."""

    def test_create_usage_pattern_with_timeseries(self, complete_system_in_browser: ModelBuilderPage):
        """Test creating a usage pattern with full timeseries configuration.

        Uses complete system fixture that has UJ, steps, server, service, job.
        """
        model_builder = complete_system_in_browser
        side_panel = model_builder.side_panel
        page = model_builder.page

        up_name = "New Usage Pattern"
        uj_name = "Test Journey"

        model_builder.click_add_usage_pattern()
        side_panel.fill_field("UsagePattern_name", up_name)

        # Set modeling duration
        page.locator("#UsagePattern_hourly_usage_journey_starts__modeling_duration_value").fill("2")
        page.locator("#UsagePattern_hourly_usage_journey_starts__modeling_duration_value").dispatch_event("change")

        # Chart should be hidden until volume is set
        expect(page.locator("#chartTimeseries")).to_contain_class("d-none")

        # Set initial volume - chart should appear
        page.locator("#UsagePattern_hourly_usage_journey_starts__initial_volume").fill("1000")
        expect(page.locator("#chartTimeseries")).not_to_have_class("d-none")

        # Clear volume - chart should hide again
        page.locator("#UsagePattern_hourly_usage_journey_starts__initial_volume").fill("")
        page.locator("#UsagePattern_hourly_usage_journey_starts__initial_volume").dispatch_event("change")
        expect(page.locator("#chartTimeseries")).to_contain_class("d-none")

        page.locator("#UsagePattern_hourly_usage_journey_starts__initial_volume").fill("1000")

        # Set growth rate
        page.locator("#UsagePattern_hourly_usage_journey_starts__net_growth_rate_in_percentage").fill("25")
        page.locator("#UsagePattern_hourly_usage_journey_starts__net_growth_rate_in_percentage").dispatch_event("change")
        side_panel.select_option("UsagePattern_hourly_usage_journey_starts__net_growth_rate_timespan", "year")

        # Select usage journey
        side_panel.select_option("UsagePattern_usage_journey", uj_name)
        side_panel.submit_and_wait_for_close()

        model_builder.object_should_exist("UsagePattern", up_name)
