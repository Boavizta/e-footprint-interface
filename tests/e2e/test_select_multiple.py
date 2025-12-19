"""Tests for select-multiple behavior when linking jobs to usage journey steps."""
import json
from copy import deepcopy

import pytest
from efootprint.core.hardware.storage import Storage
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.core.hardware.server import Server
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from playwright.sync_api import expect

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage
from tests.e2e.pages.components import ObjectCard
from tests.e2e.utils import EMPTY_SYSTEM_DICT


@pytest.fixture
def multiple_jobs_model_builder(model_builder_page: ModelBuilderPage) -> ModelBuilderPage:
    """Create a model with multiple jobs for testing select-multiple behavior."""
    storage = Storage.ssd()
    server = Server.from_defaults("Test server", storage=storage)
    job1 = Job.from_defaults("Test Job 1", server=server)
    job2 = Job.from_defaults("Test Job 2", server=server)
    uj_step1 = UsageJourneyStep.from_defaults("Test UJ 1", jobs=[job1])
    uj_step2 = UsageJourneyStep.from_defaults("Test UJ 2", jobs=[job2])
    uj = UsageJourney("Test UJ", uj_steps=[uj_step1, uj_step2])

    system_data = deepcopy(EMPTY_SYSTEM_DICT)
    system_data.update(system_to_json(uj, save_calculated_attributes=False))

    return load_system_dict_into_browser(model_builder_page, system_data)


@pytest.mark.e2e
class TestSelectMultipleJobs:
    """Migrate Cypress select-multiple behaviors to Playwright."""

    def test_add_and_remove_jobs_from_usage_journey_step(self, multiple_jobs_model_builder: ModelBuilderPage):
        """Add jobs via select-multiple, then remove them and verify card contents."""
        model_builder = multiple_jobs_model_builder
        page = model_builder.page

        uj_step_card = model_builder.get_object_card("UsageJourneyStep", "Test UJ 1")

        # Add Job 2 to the step
        uj_step_card.click_edit_button()
        page.locator("#add-btn-UsageJourneyStep_jobs").click()
        page.wait_for_timeout(50)
        model_builder.side_panel.submit_and_wait_for_close()

        # Verify Job 2 now appears on the card
        job2_card_in_step = ObjectCard(uj_step_card.locator.locator(f"div[id^='Job-']").filter(has_text="Test Job 2"))
        job2_card_in_step.should_exist()
        # Job card ID is of the form 'Job-2df3a0_in_UsageJourneyStep-2331a3_in_UsageJourney-bc6c5e'
        job2_id = job2_card_in_step.locator.get_attribute("id")[4:10]

        # Remove Job 2
        uj_step_card.click_edit_button()
        page.locator(f"#remove-{job2_id}").click()
        page.wait_for_timeout(50)
        model_builder.side_panel.submit_and_wait_for_close()

        # Job 2 should be removed
        expect(uj_step_card.locator.locator("div").filter(has_text="Test Job 2")).not_to_be_visible()

        # Remove Job 1 (last remaining job)
        job1_card_in_step = ObjectCard(uj_step_card.locator.locator(f"div[id^='Job-']").filter(has_text="Test Job 1"))
        job1_card_in_step.should_exist()
        job1_id = job1_card_in_step.locator.get_attribute("id")[4:10]
        uj_step_card.click_edit_button()
        page.locator(f"#remove-{job1_id}").click()
        page.wait_for_timeout(50)
        model_builder.side_panel.submit_and_wait_for_close()

        # Job 1 should also be removed
        expect(uj_step_card.locator.locator("div").filter(has_text="Test Job 1")).not_to_be_visible()
