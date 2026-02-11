"""Tests for job creation."""
import pytest
from efootprint.builders.services.video_streaming import VideoStreaming
from playwright.sync_api import expect

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.system_to_json import system_to_json
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

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage
from tests.fixtures.system_builders import create_hourly_usage


@pytest.fixture
def model_with_server_service_no_jobs(model_builder_page: ModelBuilderPage):
    """Create a system with server, service, and UJ steps but no jobs.

    The server and service are added as orphaned objects (not connected via jobs)
    so they appear in the UI and can be selected when creating a job.
    """
    # Create basic system with usage pattern, journey, and step (no jobs)
    uj_step = UsageJourneyStep.from_defaults("Test Step", jobs=[])
    uj = UsageJourney("Test Journey", uj_steps=[uj_step])

    usage_pattern = UsagePattern(
        "Test Usage Pattern",
        usage_journey=uj,
        devices=[Device.from_defaults("Test Device")],
        network=Network.from_defaults("Test Network"),
        country=country_generator("Test Country", "TST", SourceValue(100 * u.g / u.kWh), tz("Europe/Paris"))(),
        hourly_usage_journey_starts=create_hourly_usage()
    )

    system = System("Test System", usage_patterns=[usage_pattern], edge_usage_patterns=[])
    system_dict = system_to_json(system, save_calculated_attributes=False)

    # Create orphaned server and service (not connected to system via jobs)
    storage = Storage.from_defaults("Test Storage")
    server = Server.from_defaults("Test Server", storage=storage)
    service = VideoStreaming.from_defaults("Test Service", server=server)

    # Add orphaned objects to the system dict
    system_dict["Storage"] = {storage.id: storage.to_json(save_calculated_attributes=False)}
    system_dict["Server"] = {server.id: server.to_json(save_calculated_attributes=False)}
    system_dict["VideoStreaming"] = {service.id: service.to_json(save_calculated_attributes=False)}

    return load_system_dict_into_browser(model_builder_page, system_dict)


@pytest.mark.e2e
class TestJobs:
    """Tests for job CRUD operations."""

    def test_create_web_application_job(self, model_with_server_service_no_jobs: ModelBuilderPage):
        """Test creating a VideoStreamingJob linked to a service."""
        model_builder = model_with_server_service_no_jobs
        side_panel = model_builder.side_panel
        page = model_builder.page

        job_name = "Test Web App Job"
        step_name = "Test Step"
        service_name = "Test Service"

        step_card = model_builder.get_object_card("UsageJourneyStep", step_name)
        step_card.click_add_job_button()
        page.locator("#service").wait_for(state="attached")
        side_panel.select_option("service", service_name)
        side_panel.fill_field("VideoStreamingJob_name", job_name)
        side_panel.submit_and_wait_for_close()

        expect(page.locator("div").filter(has_text=job_name).locator("button[id^='button']").first).to_be_visible()
