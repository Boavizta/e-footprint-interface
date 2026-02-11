"""Critical path E2E test - full user journey from start to results."""
import pytest
from playwright.sync_api import expect

from tests.e2e.pages import ModelBuilderPage


@pytest.mark.e2e
class TestFullJourney:
    """End-to-end test covering the complete user workflow."""

    def test_complete_model_building_workflow(self, empty_model_builder: ModelBuilderPage):
        """Build a complete model from scratch and view results.

        This test covers the critical user path:
        1. Create usage journeys
        2. Add steps to a journey
        3. Create a server with service
        4. Add jobs linking steps to services
        5. Create a usage pattern with timeseries
        6. Delete unused objects
        7. View results
        """
        model_builder = empty_model_builder
        side_panel = model_builder.side_panel
        page = model_builder.page

        # Object names
        uj_name_one = "Test E2E UJ 1"
        uj_name_two = "Test E2E UJ 2"
        step_one = "Test E2E Step 1"
        step_two = "Test E2E Step 2"
        server_name = "Test E2E Server"
        service_name = "Test E2E Service"
        job_one = "Test E2E Job 1"
        job_two = "Test E2E Job 2"
        up_name = "Test E2E Usage Pattern"

        # --- Create two usage journeys ---
        model_builder.click_add_usage_journey()
        side_panel.fill_field("UsageJourney_name", uj_name_one)
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("UsageJourney", uj_name_one)

        model_builder.click_add_usage_journey()
        side_panel.fill_field("UsageJourney_name", uj_name_two)
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("UsageJourney", uj_name_two)

        # --- Add two steps to UJ 1 ---
        uj_card = model_builder.get_object_card("UsageJourney", uj_name_one)

        uj_card.click_add_step_button()
        side_panel.should_contain_text("Add new usage journey step")
        side_panel.fill_field("UsageJourneyStep_name", step_one)
        side_panel.fill_field("UsageJourneyStep_user_time_spent", "10.1", clear_first=False)
        side_panel.submit_and_wait_for_close()
        uj_card.should_have_class("leader-line-object")

        uj_card.click_add_step_button()
        side_panel.fill_field("UsageJourneyStep_name", step_two)
        side_panel.fill_field("UsageJourneyStep_user_time_spent", "20.2", clear_first=False)
        side_panel.submit_and_wait_for_close()

        expect(page.locator("div").filter(has_text=step_one).first).to_be_visible()
        expect(page.locator("div").filter(has_text=step_two).first).to_be_visible()

        # --- Create server ---
        model_builder.click_add_server()
        side_panel.should_contain_text("Add new server")
        side_panel.select_object_type("BoaviztaCloudServer")
        side_panel.fill_field("BoaviztaCloudServer_name", server_name)
        side_panel.fill_field("BoaviztaCloudServer_instance_type", "ent1-l")
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("BoaviztaCloudServer", server_name)

        # --- Add service to server ---
        server_card = model_builder.get_object_card("BoaviztaCloudServer", server_name)
        server_card.click_add_service_button()
        side_panel.fill_field("VideoStreaming_name", service_name)
        side_panel.submit_and_wait_for_close()
        expect(page.locator("div").filter(has_text=service_name).locator("button[id^='button']").first).to_be_visible()

        # --- Add job to step 1 (VideoStreamingJob linked to service) ---
        step_card_one = model_builder.get_object_card("UsageJourneyStep", step_one)
        step_card_one.click_add_job_button()
        page.locator("#service").wait_for(state="attached")
        side_panel.select_option("service", service_name)
        side_panel.fill_field("VideoStreamingJob_name", job_one)
        side_panel.submit_and_wait_for_close()
        expect(page.locator("div").filter(has_text=job_one).locator("button[id^='button']").first).to_be_visible()

        # --- Add job to step 2 (direct server call) ---
        step_card_two = model_builder.get_object_card("UsageJourneyStep", step_two)
        step_card_two.click_add_job_button()
        page.locator("#service").wait_for(state="attached")
        side_panel.select_option("service", "direct_server_call")
        side_panel.fill_field("Job_name", job_two)
        side_panel.submit_and_wait_for_close()
        expect(page.locator("div").filter(has_text=job_two).locator("button[id^='button']").first).to_be_visible()

        # --- Create usage pattern with timeseries ---
        model_builder.click_add_usage_pattern()
        side_panel.fill_field("UsagePattern_name", up_name)

        # Set modeling duration
        page.locator("#UsagePattern_hourly_usage_journey_starts__modeling_duration_value").fill("2")
        page.locator("#UsagePattern_hourly_usage_journey_starts__modeling_duration_value").dispatch_event("change")

        # Set initial volume
        page.locator("#UsagePattern_hourly_usage_journey_starts__initial_volume").fill("1000")

        # Set growth rate
        page.locator("#UsagePattern_hourly_usage_journey_starts__net_growth_rate_in_percentage").fill("25")
        page.locator("#UsagePattern_hourly_usage_journey_starts__net_growth_rate_in_percentage").dispatch_event("change")
        side_panel.select_option("UsagePattern_hourly_usage_journey_starts__net_growth_rate_timespan", "year")

        # Select usage journey
        side_panel.select_option("UsagePattern_usage_journey", uj_name_one)
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("UsagePattern", up_name)

        # --- Delete unused UJ 2 ---
        uj_card_two = model_builder.get_object_card("UsageJourney", uj_name_two)
        uj_card_two.click_edit_button()
        side_panel.click_delete_button()
        side_panel.confirm_delete()
        model_builder.object_should_not_exist("UsageJourney", uj_name_two)

        # --- Delete default UJ ---
        default_uj = "My first usage journey"
        default_uj_card = model_builder.get_object_card("UsageJourney", default_uj)
        default_uj_card.click_edit_button()
        side_panel.click_delete_button()
        side_panel.confirm_delete()
        model_builder.object_should_not_exist("UsageJourney", default_uj)

        # --- Open and close results panel ---
        model_builder.open_result_panel()
        model_builder.result_chart_should_be_visible()
        expect(page.locator("#graph-block")).to_be_visible()
        expect(page.locator("#result-block")).to_be_visible()

        model_builder.close_result_panel()
        expect(page.locator("#lineChart")).not_to_be_visible()

        # --- Delete usage pattern ---
        up_card = model_builder.get_object_card("UsagePattern", up_name)
        up_card.click_edit_button()
        side_panel.click_delete_button()
        side_panel.confirm_delete()
        model_builder.object_should_not_exist("UsagePattern", up_name)

