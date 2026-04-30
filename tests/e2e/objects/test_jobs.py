"""Tests for job creation."""
import pytest
from efootprint.builders.services.video_streaming import VideoStreaming, VideoStreamingJob
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
from tests.e2e.utils import add_only_update
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

    # Add orphaned objects to the system dict (service links server → storage, so one call covers all three)
    add_only_update(system_dict, system_to_json(service, save_calculated_attributes=False))

    return load_system_dict_into_browser(model_builder_page, system_dict)


@pytest.fixture
def model_with_two_steps_one_job(model_builder_page: ModelBuilderPage):
    """System with one journey, two steps, one job linked to the first step only.

    Used to test the 'link existing' button: the step that already holds the only
    job should not show the button; the empty step should.
    """
    storage = Storage.from_defaults("Test Storage")
    server = Server.from_defaults("Test Server", storage=storage)
    service = VideoStreaming.from_defaults("Test Service", server=server)
    job = VideoStreamingJob.from_defaults("Test Job", service=service)

    step_with_job = UsageJourneyStep.from_defaults("Step With Job", jobs=[job])
    step_without_job = UsageJourneyStep.from_defaults("Step Without Job", jobs=[])
    uj = UsageJourney("Test Journey", uj_steps=[step_with_job, step_without_job])

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
        page.locator("#service_or_external_api").wait_for(state="attached")
        side_panel.select_option("service_or_external_api", service_name)
        side_panel.fill_field("VideoStreamingJob_name", job_name)
        side_panel.submit_and_wait_for_close()

        expect(page.locator("div").filter(has_text=job_name).locator("button[id^='button']").first).to_be_visible()

    def test_link_existing_job_to_step(self, model_with_two_steps_one_job: ModelBuilderPage):
        """Link an existing job to a second step and verify button state updates across steps.

        Verifies:
        1. Initial: Step With Job has no 'link existing' button; Step Without Job has one.
        2. After linking Test Job to Step Without Job: Step Without Job's button disappears (1→0).
        3. After creating New Job in Step Without Job: Step With Job's button appears (0→1).
        4. After deleting New Job: Step With Job's button disappears (1→0).
        """
        model_builder = model_with_two_steps_one_job
        side_panel = model_builder.side_panel
        page = model_builder.page

        step_with_job = model_builder.get_object_card("UsageJourneyStep", "Step With Job")
        step_without_job = model_builder.get_object_card("UsageJourneyStep", "Step Without Job")

        # 1. Initial state
        assert not step_with_job.has_link_existing_child_button("JobBase")
        assert step_without_job.has_link_existing_child_button("JobBase")

        # 2. Link Test Job to Step Without Job → its button disappears (count 1→0)
        step_without_job.click_link_existing_child_button("JobBase")
        side_panel.should_be_visible()
        side_panel.should_contain_text("Link existing")
        side_panel.add_to_select_multiple("UsageJourneyStep_jobs", "Test Job")
        side_panel.submit_and_wait_for_close()

        expect(step_without_job.locator.locator("button[id^='button-']").filter(has_text="Test Job")).to_be_visible()
        assert not step_without_job.has_link_existing_child_button("JobBase")

        # 3. Create New Job in Step Without Job → Step With Job's button appears (count 0→1)
        step_without_job.click_add_job_button()
        page.locator("#service_or_external_api").wait_for(state="attached")
        side_panel.select_option("service_or_external_api", "Test Service")
        side_panel.fill_field("VideoStreamingJob_name", "New Job")
        side_panel.submit_and_wait_for_close()

        assert step_with_job.has_link_existing_child_button("JobBase")

        # 4. Delete New Job → Step With Job's button disappears (count 1→0)
        new_job_card = model_builder.get_object_card("VideoStreamingJob", "New Job")
        new_job_card.click_edit_button()
        side_panel.click_delete_button()
        side_panel.confirm_delete()

        assert not step_with_job.has_link_existing_child_button("JobBase")
