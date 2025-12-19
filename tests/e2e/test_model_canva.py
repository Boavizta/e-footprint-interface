"""Tests for model canvas interactions migrated from Cypress."""
import pytest

from tests.e2e.pages import ModelBuilderPage


@pytest.mark.e2e
class TestModelCanvas:
    """Model canvas behaviors (job creation buttons, accordion ordering)."""

    def test_edit_usage_journey_keeps_steps_visible(self, model_builder_page: ModelBuilderPage):
        """Editing a usage journey without changes should keep its steps intact."""
        model_builder = model_builder_page.goto()

        uj_card = model_builder.get_object_card("UsageJourney", "My first usage journey")
        uj_card.click_edit_button()
        model_builder.side_panel.submit_and_wait_for_close()

        model_builder.get_object_card("UsageJourneyStep", "My first usage journey step").should_exist()

    def test_verify_add_job_button_layout(self, minimal_complete_model_builder: ModelBuilderPage):
        """Verify button ordering in accordion."""
        model_builder = minimal_complete_model_builder
        uj_step_card = model_builder.get_object_card("UsageJourneyStep", "Test Step")

        # Expand accordion to check ordering: job button should be above add job button
        accordion_toggle = uj_step_card.locator.locator("button[data-bs-target^='#flush-']").first
        accordion_toggle.click()
        accordion_container = uj_step_card.locator.locator("div[id^='flush-']").first

        job_button = accordion_container.locator("button", has_text="Test job").first
        add_job_button = accordion_container.locator("button[hx-get='/model_builder/open-create-object-panel/JobBase/']").first

        job_top = job_button.evaluate("el => el.getBoundingClientRect().top")
        add_top = add_job_button.evaluate("el => el.getBoundingClientRect().top")

        assert add_top > job_top, "Add job button should appear below existing job buttons"
