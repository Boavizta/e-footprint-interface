"""Tests for ExternalAPI objects - EcoLogitsGenAI external API full workflow."""
import pytest
from playwright.sync_api import expect

from tests.e2e.pages import ModelBuilderPage
from tests.e2e.utils import click_and_wait_for_htmx


@pytest.mark.e2e
class TestExternalAPIObjects:
    """Tests for EcoLogitsGenAI external API creation, job linkage, and calculated attributes."""

    def test_ecologits_genai_full_workflow(self, empty_model_builder: ModelBuilderPage):
        """Test full workflow: create EcoLogitsGenAIExternalAPI, add job, usage pattern, check results
        and EcoLogits formula, then delete the job without raising an error."""
        model_builder = empty_model_builder
        side_panel = model_builder.side_panel
        page = model_builder.page

        api_name = "Test GenAI API"
        job_name = "Test GenAI Job"
        usage_pattern_name = "Test Usage Pattern"
        uj_name = "My first usage journey"
        uj_step_name = "My first usage journey step"

        # Step 1: Create EcoLogitsGenAIExternalAPI (defaults to provider=anthropic, model=claude-opus-4-5)
        model_builder.click_add_external_api()
        page.locator("#sidePanelForm").wait_for(state="visible")
        side_panel.fill_field("EcoLogitsGenAIExternalAPI_name", api_name)
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("EcoLogitsGenAIExternalAPI", api_name)

        # Step 2: Create EcoLogitsGenAIExternalAPIJob linked to the external API
        uj_step_card = model_builder.get_object_card("UsageJourneyStep", uj_step_name)
        uj_step_card.click_add_job_button()
        page.locator("#service_or_external_api").wait_for(state="attached")
        side_panel.select_option("service_or_external_api", api_name)
        page.locator("#EcoLogitsGenAIExternalAPIJob_name").wait_for(state="attached")
        side_panel.fill_field("EcoLogitsGenAIExternalAPIJob_name", job_name)
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("EcoLogitsGenAIExternalAPIJob", job_name)

        # Step 3: Create a usage pattern linked to the default usage journey
        model_builder.click_add_usage_pattern()
        side_panel.fill_field("UsagePattern_name", usage_pattern_name)
        page.locator("#UsagePattern_hourly_usage_journey_starts__initial_volume").fill("1000")
        side_panel.select_option("UsagePattern_usage_journey", uj_name)
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("UsagePattern", usage_pattern_name)

        # Step 4: Check that results are computed (chart is visible with data)
        model_builder.open_result_panel()
        model_builder.result_chart_should_be_visible()
        model_builder.close_result_panel()

        # Step 5: Navigate to EcoLogitsGenAIExternalAPIJob calculated attributes
        uj_step_card = model_builder.get_object_card("UsageJourneyStep", uj_step_name)
        uj_step_card.open_accordion()
        job_card = model_builder.get_object_card("EcoLogitsGenAIExternalAPIJob", job_name)
        job_card.click_edit_button()

        # Open the calculated attributes accordion
        calc_attrs_btn = page.locator(
            "[data-bs-target='#collapseCalculatedAttributesEcoLogitsGenAIExternalAPIJob']"
        )
        calc_attrs_btn.click()
        page.locator("#collapseCalculatedAttributesEcoLogitsGenAIExternalAPIJob").wait_for(state="visible")

        # Click the formula button for "Generation latency" and wait for HTMX to load the explanation
        formula_btn = page.locator("[data-bs-target='#collapse-calculated_attributes-generation_latency']")
        click_and_wait_for_htmx(page, formula_btn)

        # Check that the EcoLogits computation code is non-empty
        explanation = page.locator("#collapse-calculated_attributes-generation_latency")
        expect(explanation.locator(".explainable-formula pre")).not_to_be_empty()

        # Check that Input Variables section has at least one entry
        expect(explanation.locator(".explainable-ancestors li").first).to_be_visible()

        # Step 6: Delete the job and verify no error is raised
        side_panel.click_delete_button()
        side_panel.confirm_delete()
        model_builder.object_should_not_exist("EcoLogitsGenAIExternalAPIJob", job_name)
        expect(page.locator("#model-builder-modal")).not_to_be_visible()
