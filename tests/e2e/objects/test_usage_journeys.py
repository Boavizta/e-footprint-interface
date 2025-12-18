"""Tests for usage journey and usage journey step creation/editing/deletion."""
import pytest
from playwright.sync_api import expect

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.constants.countries import country_generator, tz
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.system import System

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage
from tests.fixtures.system_builders import create_hourly_usage


@pytest.fixture
def system_dict_with_usage_journey():
    """Create a system dict with a usage journey (no steps yet)."""
    uj = UsageJourney("Test Journey", uj_steps=[])

    usage_pattern = UsagePattern(
        "Test Usage Pattern",
        usage_journey=uj,
        devices=[Device.from_defaults("Test Device")],
        network=Network.from_defaults("Test Network"),
        country=country_generator("Test Country", "TST", SourceValue(100 * u.g / u.kWh), tz("Europe/Paris"))(),
        hourly_usage_journey_starts=create_hourly_usage()
    )

    system = System("Test System", usage_patterns=[usage_pattern], edge_usage_patterns=[])
    return system_to_json(system, save_calculated_attributes=False)


@pytest.fixture
def model_with_usage_journey(model_builder_page: ModelBuilderPage, system_dict_with_usage_journey):
    """Load system dict with a usage journey into browser."""
    return load_system_dict_into_browser(model_builder_page, system_dict_with_usage_journey)


@pytest.mark.e2e
class TestUsageJourneys:
    """Tests for usage journey CRUD operations."""

    def test_create_multiple_usage_journeys(self, model_with_usage_journey: ModelBuilderPage):
        """Test creating multiple usage journeys."""
        model_builder = model_with_usage_journey
        side_panel = model_builder.side_panel

        uj_names = ["UJ Alpha", "UJ Beta", "UJ Gamma"]

        for name in uj_names:
            model_builder.click_add_usage_journey()
            side_panel.fill_field("UsageJourney_name", name)
            side_panel.submit_and_wait_for_close()

        for name in uj_names:
            model_builder.object_should_exist("UsageJourney", name)

    def test_delete_usage_journey(self, model_with_usage_journey: ModelBuilderPage):
        """Test deleting a usage journey."""
        model_builder = model_with_usage_journey
        side_panel = model_builder.side_panel
        page = model_builder.page

        # Create a UJ to delete
        uj_name = "UJ To Delete"
        model_builder.click_add_usage_journey()
        side_panel.fill_field("UsageJourney_name", uj_name)
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("UsageJourney", uj_name)

        # Delete it
        uj_card = model_builder.get_object_card("UsageJourney", uj_name)
        uj_card.click_edit_button()
        side_panel.click_delete_button()
        side_panel.confirm_delete()

        model_builder.object_should_not_exist("UsageJourney", uj_name)
        expect(page.locator("#model-builder-modal")).not_to_be_visible()


@pytest.mark.e2e
class TestUsageJourneySteps:
    """Tests for usage journey step operations."""

    def test_add_multiple_steps_to_usage_journey(self, model_with_usage_journey: ModelBuilderPage):
        """Test adding multiple steps to a usage journey."""
        model_builder = model_with_usage_journey
        side_panel = model_builder.side_panel
        page = model_builder.page

        uj_name = "Test Journey"
        steps = [
            ("Step One", "10"),
            ("Step Two", "20"),
            ("Step Three", "30"),
        ]

        uj_card = model_builder.get_object_card("UsageJourney", uj_name)

        for step_name, time_spent in steps:
            uj_card.click_add_step_button()
            side_panel.fill_field("UsageJourneyStep_name", step_name)
            side_panel.fill_field("UsageJourneyStep_user_time_spent", time_spent, clear_first=False)
            side_panel.submit_and_wait_for_close()

        # Verify all steps were added
        for step_name, _ in steps:
            expect(page.locator("div").filter(has_text=step_name).first).to_be_visible()
