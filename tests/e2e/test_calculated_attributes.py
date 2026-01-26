"""Tests for navigating calculated attributes in job forms."""
import pytest
from efootprint.core.system import System
from playwright.sync_api import expect

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.constants.countries import country_generator, tz
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.usage.usage_pattern import UsagePattern

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage
from tests.e2e.utils import click_and_wait_for_htmx
from tests.fixtures.system_builders import create_hourly_usage


@pytest.fixture
def system_with_multiple_usage_patterns(minimal_system: System, model_builder_page: ModelBuilderPage):
    """Create a complete system with two usage patterns for calculated attributes navigation."""
    country = country_generator(
        "Alt Country", "ALT", SourceValue(120 * u.g / u.kWh), tz("Europe/Paris"))()

    extra_usage_pattern = UsagePattern(
        "Calc Attr Usage Pattern 2",
        usage_journey=minimal_system.usage_journeys[0],
        devices=[Device.from_defaults("Calc Device 2")],
        network=Network.from_defaults("Calc Network 2"),
        country=country,
        hourly_usage_journey_starts=create_hourly_usage()
    )
    minimal_system.usage_patterns.append(extra_usage_pattern)

    system_dict = system_to_json(minimal_system, save_calculated_attributes=False)
    return load_system_dict_into_browser(model_builder_page, system_dict)


@pytest.mark.e2e
class TestCalculatedAttributes:
    """Calculated attributes navigation and chart rendering."""

    def test_navigate_calculated_attributes(self, system_with_multiple_usage_patterns: ModelBuilderPage):
        """Navigate between calculated attributes and verify charts/explanations render."""
        model_builder = system_with_multiple_usage_patterns
        page = model_builder.page

        # Open the job form
        uj_step_card = model_builder.get_object_card("UsageJourneyStep", "Test Step")
        uj_step_card.open_accordion()
        job_card = model_builder.get_object_card("Job", "Test Job")
        job_card.click_edit_button()

        # Expand calculated attributes section
        calc_toggle = page.locator("button[data-bs-target='#collapseCalculatedAttributesJob']")
        expect(calc_toggle).to_be_visible()
        calc_toggle.click()

        # Open hourly_occurrences_per_usage_pattern group
        pattern_group_toggle = page.locator(
            "button[data-bs-target^='#collapse-calculated_attributes_hourly_occurrences_per_usage_pattern']"
        )
        expect(pattern_group_toggle).to_be_enabled()
        pattern_group_toggle.click()

        # Click a specific usage-pattern chart link and verify chart is available
        chart_button = page.locator("button[hx-get*='hourly_occurrences_per_usage_pattern']").first
        click_and_wait_for_htmx(page, chart_button)
        chart_exists = page.evaluate("window.calculatedAttributesChart !== undefined")
        assert chart_exists, "calculatedAttributesChart should be defined after loading chart"

        # Switch to hourly_avg_occurrences_across_usage_patterns
        avg_button = page.locator("button[hx-get*='hourly_avg_occurrences_across_usage_patterns']").first
        click_and_wait_for_htmx(page, avg_button)
        chart_exists = page.evaluate("window.calculatedAttributesChart !== undefined")
        assert chart_exists, "calculatedAttributesChart should remain defined after switching chart"

        # Open non-chart attribute duration and verify explanation panel
        model_builder.side_panel.close()
        uj_card = model_builder.get_object_card("UsageJourney", "Test Journey")
        uj_card.click_edit_button()
        calc_toggle = page.locator("button[data-bs-target='#collapseCalculatedAttributesUsageJourney']")
        expect(calc_toggle).to_be_visible()
        calc_toggle.click()
        duration_button = page.locator("button[hx-get*='duration/']").first
        click_and_wait_for_htmx(page, duration_button)

        hx_attr = duration_button.get_attribute("hx-get") or ""
        parts = [p for p in hx_attr.split("/") if p]
        uj_id = parts[2] if len(parts) >= 3 else ""
        explanation_locator = page.locator(f"#ancestors-formula-and-children-duration-in-{uj_id}")
        expect(explanation_locator).to_be_visible()
        # Assert that the #explainable-ancestors element contains a list with at least one item, to make sure that
        # calculus graph data isn’t corrupted
        list_items = explanation_locator.locator("div.explainable-ancestors").locator("ul > li")
        expect(list_items).not_to_have_count(0)
