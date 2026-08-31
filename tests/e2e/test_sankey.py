"""E2E tests for the Sankey impact repartition section.

Uses a system with Server, Storage, Device, Network, UsagePattern, and Job
so all chip types are non-empty and meaningful assertions can be made.
"""

import pytest
from django.template.loader import render_to_string
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.services.video_streaming import VideoStreaming
from efootprint.constants.countries import country_generator, tz
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.builders.services.video_streaming import VideoStreamingJob

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage
from tests.e2e.pages.sankey_page import SankeyPage
from tests.fixtures.system_builders import create_hourly_usage


@pytest.fixture
def sankey_system(model_builder_page: ModelBuilderPage) -> ModelBuilderPage:
    """System with Server, Storage, Device, Network, UsagePattern, and VideoStreamingJob.

    Ensures all chip types (exclude/skip) have at least some classes present.
    """
    storage = Storage.from_defaults("Test Storage")
    server = Server.from_defaults("Test Server", storage=storage)
    service = VideoStreaming.from_defaults("Test Service", server=server)
    device = Device.from_defaults("Test Device")
    network = Network.from_defaults("Test Network")
    country = country_generator("Test Country", "TST", SourceValue(100 * u.g / u.kWh), tz("Europe/Paris"))()
    uj_step = UsageJourneyStep.from_defaults(
        "Test Step", jobs=[VideoStreamingJob.from_defaults("Test Job", service=service)]
    )
    uj = UsageJourney("Test Journey", uj_steps=[uj_step])
    usage_pattern = UsagePattern(
        "Test UP",
        usage_journey=uj,
        devices=[device],
        network=network,
        country=country,
        hourly_usage_journey_starts=create_hourly_usage(),
    )
    system = System("Test System", usage_patterns=[usage_pattern], edge_usage_patterns=[])
    system_dict = system_to_json(system, save_computed_state=False)
    return load_system_dict_into_browser(model_builder_page, system_dict)


@pytest.mark.e2e
class TestSankeySection:

    def test_memory_limit_guidance_replaces_graph_but_keeps_card_controls(self, sankey_system: ModelBuilderPage):
        sankey_system.open_result_panel()
        card = SankeyPage(sankey_system).first_card()
        card.wait_for_diagram_update()
        response_html = render_to_string(
            "model_builder/result/sankey_memory_limit.html",
            {"card_id": card.card_id, "coverage_percent": 33, "capacity_gib": 4.0},
        )
        sankey_system.page.route(
            "**/model_builder/sankey-diagram/",
            lambda route: route.fulfill(status=200, content_type="text/html", body=response_html),
        )

        card.set_lifecycle_filter("Manufacturing")

        guidance = card.memory_limit_guidance_locator()
        guidance.wait_for(state="visible")
        assert "33%" in guidance.inner_text()
        assert "completion coverage only" in guidance.inner_text()
        assert "4.0 GiB" in guidance.inner_text()
        assert card.settings_visible()
        assert sankey_system.page.locator("#model-builder-modal").count() == 0

    def test_first_diagram_auto_renders_on_result_panel_open(self, sankey_system: ModelBuilderPage):
        """Opening the result panel auto-generates the first Sankey with default settings."""
        sankey_system.open_result_panel()
        sankey_page = SankeyPage(sankey_system)
        card = sankey_page.first_card()
        card.wait_for_diagram_update()

        assert card.settings_visible()
        assert card.diagram_is_rendered()
        assert card.title_text()  # non-empty title

    def test_first_card_title_contains_system_name(self, sankey_system: ModelBuilderPage):
        """Card title should include the system name after rendering."""
        sankey_system.open_result_panel()
        card = SankeyPage(sankey_system).first_card()
        card.wait_for_diagram_update()

        assert "Test System" in card.title_text()

    def test_changing_lifecycle_filter_updates_title(self, sankey_system: ModelBuilderPage):
        """Changing the lifecycle filter updates the diagram title."""
        sankey_system.open_result_panel()
        card = SankeyPage(sankey_system).first_card()
        card.wait_for_diagram_update()

        title_before = card.title_text()
        card.set_lifecycle_filter("Manufacturing")

        assert "manufacturing" in card.title_text().lower()
        assert card.title_text() != title_before
        assert card.diagram_is_rendered()

    def test_two_cards_are_independent(self, sankey_system: ModelBuilderPage):
        """Changing settings on card 2 does not affect card 1."""
        sankey_system.open_result_panel()
        sankey_page = SankeyPage(sankey_system)
        card1 = sankey_page.first_card()
        card1.wait_for_diagram_update()

        title1_before = card1.title_text()

        card2 = sankey_page.add_card()
        card2.set_lifecycle_filter("Manufacturing")

        # card1 title must not have changed
        assert card1.title_text() == title1_before

    def test_first_diagram_stays_rendered_after_adding_second_card(self, sankey_system: ModelBuilderPage):
        """Adding a second card must not purge the first card's Plotly diagram."""
        sankey_system.open_result_panel()
        sankey_page = SankeyPage(sankey_system)
        card1 = sankey_page.first_card()
        card1.wait_for_diagram_update()

        assert card1.diagram_is_rendered()

        sankey_page.add_card()

        # card1 diagram must still be rendered after the second card was appended
        assert card1.diagram_is_rendered()

    def test_add_and_remove_cards(self, sankey_system: ModelBuilderPage):
        """Cards can be added and removed; removal is client-side only."""
        sankey_system.open_result_panel()
        sankey_page = SankeyPage(sankey_system)
        sankey_page.first_card().wait_for_diagram_update()

        assert len(sankey_page.cards()) == 1

        card2 = sankey_page.add_card()
        assert len(sankey_page.cards()) == 2

        card2.remove()
        assert len(sankey_page.cards()) == 1

    def test_onboarding_banner_dismissal_persists(self, sankey_system: ModelBuilderPage):
        """Dismissing the onboarding banner stores the preference in localStorage."""
        sankey_system.open_result_panel()
        sankey_page = SankeyPage(sankey_system)

        assert sankey_page.onboarding_banner_visible()

        sankey_page.dismiss_onboarding_banner()
        assert not sankey_page.onboarding_banner_visible()

        # Re-open result panel — banner must remain dismissed (localStorage)
        sankey_system.close_result_panel()
        sankey_system.open_result_panel()
        assert not SankeyPage(sankey_system).onboarding_banner_visible()

    def test_zero_threshold_persists_when_results_close_immediately(self, sankey_system: ModelBuilderPage):
        sankey_system.open_result_panel()
        card = SankeyPage(sankey_system).first_card()
        card.wait_for_diagram_update()

        card.set_aggregation_threshold_without_wait(0)
        sankey_system.close_result_panel()
        sankey_system.open_result_panel()

        restored_card = SankeyPage(sankey_system).first_card()
        restored_card.wait_for_diagram_update()
        assert restored_card.aggregation_threshold() == 0

    def test_analyse_by_chip_toggle_triggers_diagram_update(self, sankey_system: ModelBuilderPage):
        """Toggling an analyse-by chip triggers a live diagram update."""
        sankey_system.open_result_panel()
        card = SankeyPage(sankey_system).first_card()
        card.wait_for_diagram_update()

        card.toggle_analyse_by_chip("Usage journeys")
        assert card.diagram_is_rendered()

    def test_settings_panel_open_by_default_on_new_card(self, sankey_system: ModelBuilderPage):
        """Settings panel is visible when a new card is added."""
        sankey_system.open_result_panel()
        sankey_page = SankeyPage(sankey_system)
        sankey_page.first_card().wait_for_diagram_update()

        card2 = sankey_page.add_card()
        assert card2.settings_visible()

    def test_chip_lists_filtered_to_system_classes(self, sankey_system: ModelBuilderPage):
        """Analyse-by and exclude chip lists only show relevant items."""
        sankey_system.open_result_panel()
        card = SankeyPage(sankey_system).first_card()
        card.wait_for_diagram_update()

        # Analyse-by chips for present columns should appear
        assert card.analyse_by_chip_exists("Usage journeys")
        assert card.analyse_by_chip_exists("Phase")

        # Exclude chips in advanced — edge device not in this system
        card.open_advanced()
        assert not card.exclude_chip_exists("Edge device")

    def test_exclude_chip_updates_diagram_title(self, sankey_system: ModelBuilderPage):
        """Excluding an object type updates the title to mention it."""
        sankey_system.open_result_panel()
        card = SankeyPage(sankey_system).first_card()
        card.wait_for_diagram_update()
        card.open_advanced()

        title_before = card.title_text()
        card.toggle_exclude_chip("Device")

        assert "excluding" in card.title_text().lower()
        assert card.title_text() != title_before
