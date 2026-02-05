"""Tests for edge objects - edge devices, edge usage journeys, edge functions."""
from copy import deepcopy

import pytest
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from playwright.sync_api import expect

from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage
from tests.e2e.pages.components import ObjectCard
from tests.e2e.utils import EMPTY_SYSTEM_DICT, add_only_update


@pytest.fixture
def edge_system_in_browser(model_builder_page: ModelBuilderPage):
    """Create and load a system with one edge device shared by two edge usage journeys."""
    edge_storage = EdgeStorage.from_defaults("Edge Storage")
    edge_device = EdgeComputer.from_defaults("Shared Edge Device", storage=edge_storage)

    # Create two edge functions using the same device
    process1 = RecurrentEdgeProcess.from_defaults("Process on Journey 1", edge_device=edge_device)
    process2 = RecurrentEdgeProcess.from_defaults("Process on Journey 2", edge_device=edge_device)

    edge_function1 = EdgeFunction("Function in Journey 1", recurrent_edge_device_needs=[process1],
    recurrent_server_needs=[])
    edge_function2 = EdgeFunction("Function in Journey 2", recurrent_edge_device_needs=[process2],
    recurrent_server_needs=[])

    journey1 = EdgeUsageJourney.from_defaults(name="Edge Journey 1", edge_functions=[edge_function1])
    journey2 = EdgeUsageJourney.from_defaults(name="Edge Journey 2", edge_functions=[edge_function2])

    system_data = deepcopy(EMPTY_SYSTEM_DICT)
    system_data.update(system_to_json(journey1, save_calculated_attributes=False))
    add_only_update(system_data, system_to_json(journey2, save_calculated_attributes=False))

    return load_system_dict_into_browser(model_builder_page, system_data)


@pytest.fixture
def edge_system_with_mirrored_edge_functions(model_builder_page: ModelBuilderPage):
    """Create and load a system with one edge device shared by two edge usage journeys."""
    edge_storage = EdgeStorage.from_defaults("Edge Storage")
    edge_device = EdgeComputer.from_defaults("Shared Edge Device", storage=edge_storage)

    # Create two edge functions using the same device
    process1 = RecurrentEdgeProcess.from_defaults("Process on Journey 1", edge_device=edge_device)
    process2 = RecurrentEdgeProcess.from_defaults("Process on Journey 2", edge_device=edge_device)

    edge_function = EdgeFunction("Mirrored function, referenced in journey 1 and 2",
                                  recurrent_edge_device_needs=[process1, process2],
                                  recurrent_server_needs=[])

    journey1 = EdgeUsageJourney.from_defaults(name="Edge Journey 1", edge_functions=[edge_function])
    journey2 = EdgeUsageJourney.from_defaults(name="Edge Journey 2", edge_functions=[edge_function])

    system_data = deepcopy(EMPTY_SYSTEM_DICT)
    system_data.update(system_to_json(journey1, save_calculated_attributes=False))
    add_only_update(system_data, system_to_json(journey2, save_calculated_attributes=False))

    return load_system_dict_into_browser(model_builder_page, system_data)


@pytest.mark.e2e
class TestEdgeObjects:
    """Tests for edge device and edge usage journey workflows."""

    def test_create_edge_device_with_edge_usage_journey(self, empty_model_builder: ModelBuilderPage):
        """Create edge device, edge usage journey, edge function, and recurrent process."""
        model_builder = empty_model_builder
        side_panel = model_builder.side_panel
        page = model_builder.page

        edge_device_name = "Test Edge Device"
        edge_journey_name = "Test Edge Journey"
        edge_function_name = "Test Edge Function"
        recurrent_process_name = "Test Recurrent Process"
        recurrent_server_need_name = "Test Recurrent Server Need"
        server_name = "Test Server"
        job_name = "Test Server Job"
        edge_usage_pattern_name = "Test Edge Usage Pattern"

        # Create edge usage journey
        page.locator("#btn-add-edge-usage-journey").click()
        page.locator("#sidePanelForm").wait_for(state="visible")
        side_panel.fill_field("EdgeUsageJourney_name", edge_journey_name)
        side_panel.fill_field("EdgeUsageJourney_usage_span", "6")
        side_panel.submit_and_wait_for_close()

        model_builder.object_should_exist("EdgeUsageJourney", edge_journey_name)

        # Add edge function to edge usage journey
        edge_journey_card = model_builder.get_object_card("EdgeUsageJourney", edge_journey_name)
        edge_journey_card.click_add_step_button()
        side_panel.fill_field("EdgeFunction_name", edge_function_name)
        side_panel.submit_and_wait_for_close()

        model_builder.object_should_exist("EdgeFunction", edge_function_name)

        edge_function_card = model_builder.get_object_card("EdgeFunction", edge_function_name)

        # Try to add recurrent edge process before creating an edge device - should show error
        edge_function_card.click_add_child_button("RecurrentEdgeDeviceNeed")
        model_builder.expect_error_modal(
            "Please create an edge device before adding a recurrent edge resource need")
        model_builder.close_error_modal("model-builder-modal")

        # Try to add a recurrent server need before creating an edge device - should show error
        edge_function_card.click_add_child_button("RecurrentServerNeed")
        model_builder.expect_error_modal(
            "Please create an edge device before adding a recurrent server need")
        model_builder.close_error_modal("model-builder-modal")

        # Create edge device
        page.locator("#btn-add-edge-device").click()
        page.locator("#sidePanelForm").wait_for(state="visible")
        side_panel.select_object_type("EdgeComputer")
        side_panel.fill_field("EdgeComputer_name", edge_device_name)
        side_panel.fill_field("EdgeComputer_ram", "16")
        side_panel.fill_field("EdgeComputer_compute", "8")
        side_panel.submit_and_wait_for_close()

        model_builder.object_should_exist("EdgeComputer", edge_device_name)

        # Add recurrent edge process to edge function
        edge_function_card.click_add_child_button("RecurrentEdgeDeviceNeed")
        page.locator("#sidePanelForm").wait_for(state="visible")

        # Select edge device and fill recurrent process details
        side_panel.select_option("edge_device", edge_device_name)
        side_panel.fill_field("RecurrentEdgeProcess_name", recurrent_process_name)
        side_panel.fill_field("RecurrentEdgeProcess_recurrent_compute_needed", "2.5")
        side_panel.fill_field("RecurrentEdgeProcess_recurrent_ram_needed", "4.5")
        side_panel.fill_field("RecurrentEdgeProcess_recurrent_storage_needed", "0")
        side_panel.submit_and_wait_for_close()

        model_builder.object_should_exist("RecurrentEdgeProcess", recurrent_process_name)

        # Add a recurrent server need
        edge_function_card.click_add_child_button("RecurrentServerNeed")
        side_panel.fill_field("RecurrentServerNeed_name", recurrent_server_need_name)
        side_panel.select_option("RecurrentServerNeed_edge_device", edge_device_name)
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("RecurrentServerNeed", recurrent_server_need_name)

        # Try to add a job to the recurrent server need - should show error since no server
        edge_function_card.open_accordion()
        recurrent_server_need_card = model_builder.get_object_card("RecurrentServerNeed", recurrent_server_need_name)
        recurrent_server_need_card.click_add_job_button()
        model_builder.expect_error_modal(
            "Please go to the infrastructure section and create a server before adding a job"
        ).close_error_modal()

        # Add a server
        model_builder.click_add_server()
        side_panel.select_object_type("BoaviztaCloudServer")
        side_panel.fill_field("BoaviztaCloudServer_name", server_name)
        side_panel.fill_field("BoaviztaCloudServer_instance_type", "ent1-l")
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("BoaviztaCloudServer", server_name)

        # Add a job to the recurrent server need - should work
        recurrent_server_need_card.click_add_job_button()
        page.locator("#service").wait_for(state="attached")
        side_panel.select_option("service", "direct_server_call")
        side_panel.fill_field("Job_name", job_name)
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("Job", job_name)

        # Add edge usage pattern
        model_builder.click_add_edge_usage_pattern()
        side_panel.fill_field("EdgeUsagePattern_name", edge_usage_pattern_name)
        modeling_duration_field = (
            "#EdgeUsagePattern_hourly_edge_usage_journey_starts__modeling_duration_value"
        )
        page.locator(modeling_duration_field).fill("2")
        page.locator(modeling_duration_field).dispatch_event("change")
        side_panel.fill_field(
            "EdgeUsagePattern_hourly_edge_usage_journey_starts__initial_volume",
            "1000"
        )
        side_panel.fill_field(
            "EdgeUsagePattern_hourly_edge_usage_journey_starts__net_growth_rate_in_percentage",
            "25"
        )
        page.locator(
            "#EdgeUsagePattern_hourly_edge_usage_journey_starts__net_growth_rate_in_percentage"
        ).dispatch_event("change")
        side_panel.select_option(
            "EdgeUsagePattern_hourly_edge_usage_journey_starts__net_growth_rate_timespan",
            "year"
        )
        side_panel.select_option("EdgeUsagePattern_edge_usage_journey", edge_journey_name)
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("EdgeUsagePattern", edge_usage_pattern_name)

        # Click results and check that server footprints are not zero.
        model_builder.open_result_panel()
        model_builder.result_chart_should_be_visible()
        server_energy = page.evaluate("window.emissions.values['Servers_and_storage_energy']")
        server_fabrication = page.evaluate("window.emissions.values['Servers_and_storage_fabrication']")
        assert any(value > 0 for value in server_energy) or any(value > 0 for value in server_fabrication)

    def test_edge_device_with_advanced_options(self, empty_model_builder: ModelBuilderPage):
        """Create edge device with advanced parameters."""
        model_builder = empty_model_builder
        side_panel = model_builder.side_panel
        page = model_builder.page

        edge_device_name = "Advanced Edge Device"

        # Create edge device
        page.locator("#btn-add-edge-device").click()
        page.locator("#sidePanelForm").wait_for(state="visible")
        side_panel.select_object_type("EdgeComputer")
        side_panel.fill_field("EdgeComputer_name", edge_device_name)

        # Open advanced options
        page.locator("#display-advanced-EdgeComputer").click()
        expect(page.locator("#advanced-EdgeComputer")).to_be_visible()

        # Set advanced parameters
        page.locator("#EdgeComputer_lifespan").clear()
        page.locator("#EdgeComputer_lifespan").fill("3")
        page.locator("#EdgeComputer_carbon_footprint_fabrication").clear()
        page.locator("#EdgeComputer_carbon_footprint_fabrication").fill("100")

        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("EdgeComputer", edge_device_name)

        # Verify advanced parameters were saved
        edge_device_card = model_builder.get_object_card("EdgeComputer", edge_device_name)
        edge_device_card.click_edit_button()

        page.locator("#display-advanced-EdgeComputer").click()
        expect(page.locator("#EdgeComputer_lifespan")).to_have_value("3")
        expect(page.locator("#EdgeComputer_carbon_footprint_fabrication")).to_have_value("100")

    def test_multiple_edge_journeys_share_edge_device(self, edge_system_in_browser: ModelBuilderPage):
        """Verify multiple edge usage journeys can share the same edge device."""
        model_builder = edge_system_in_browser

        # Verify both edge journeys exist
        model_builder.object_should_exist("EdgeUsageJourney", "Edge Journey 1")
        model_builder.object_should_exist("EdgeUsageJourney", "Edge Journey 2")

        # Verify the shared edge device exists
        model_builder.object_should_exist("EdgeComputer", "Shared Edge Device")

        # Verify both edge functions exist and reference the shared device
        model_builder.object_should_exist("EdgeFunction", "Function in Journey 1")
        model_builder.object_should_exist("EdgeFunction", "Function in Journey 2")

        # Verify both processes (which link functions to the device) exist
        model_builder.object_should_exist("RecurrentEdgeProcess", "Process on Journey 1")
        model_builder.object_should_exist("RecurrentEdgeProcess", "Process on Journey 2")

    def test_edge_function_name_mirroring(self, edge_system_with_mirrored_edge_functions: ModelBuilderPage):
        """Verify edge function name changes are reflected in the model."""
        model_builder = edge_system_with_mirrored_edge_functions
        side_panel = model_builder.side_panel
        page = model_builder.page

        # Edit the edge function name
        old_name = "Mirrored function, referenced in journey 1 and 2"
        function_cards = page.locator(f"div[id^='EdgeFunction-']").filter(has_text=old_name)
        expect(function_cards).to_have_count(2)
        function_card = ObjectCard(function_cards.first)
        function_card.click_edit_button()

        new_name = "Renamed Edge Function"
        page.locator("#EdgeFunction_name").clear()
        page.locator("#EdgeFunction_name").fill(new_name)
        side_panel.submit_and_wait_for_close()

        # Verify the function is now shown with the new name
        function_cards = page.locator(f"div[id^='EdgeFunction-']").filter(has_text=new_name)
        expect(function_cards).to_have_count(2)

        # Verify the old name no longer exists (card should not be found)
        old_card = model_builder.get_object_card("EdgeFunction", old_name)
        expect(old_card.locator).not_to_be_attached()

    def test_edge_device_with_cpu_ram_components_and_component_needs(self, empty_model_builder: ModelBuilderPage):
        """Create EdgeDevice with CPU and RAM components, add RecurrentEdgeDeviceNeed with component needs."""
        model_builder = empty_model_builder
        side_panel = model_builder.side_panel
        page = model_builder.page

        edge_device_name = "Test Edge Device with Components"
        cpu_component_name = "Test CPU Component"
        ram_component_name = "Test RAM Component"
        edge_journey_name = "Test Edge Journey"
        edge_function_name = "Test Edge Function"
        recurrent_need_name = "Test Recurrent Edge Device Need"
        cpu_need_name = "CPU Need"
        ram_need_name = "RAM Need"
        cpu_need_value = "2.0"
        ram_need_value = "4.0"

        # Step 1: Create EdgeDevice
        page.locator("#btn-add-edge-device").click()
        page.locator("#sidePanelForm").wait_for(state="visible")
        side_panel.select_object_type("EdgeDevice")
        side_panel.fill_field("EdgeDevice_name", edge_device_name)
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("EdgeDevice", edge_device_name)

        # Step 2: Add CPU component to EdgeDevice
        edge_device_card = model_builder.get_object_card("EdgeDevice", edge_device_name)
        edge_device_card.locator.locator("button[hx-get*='EdgeComponent']").click()
        page.locator("#sidePanelForm").wait_for(state="visible")
        side_panel.select_object_type("EdgeCPUComponent")
        side_panel.fill_field("EdgeCPUComponent_name", cpu_component_name)
        side_panel.submit_and_wait_for_close()
        cpu_card = model_builder.get_object_card("EdgeCPUComponent", cpu_component_name)
        cpu_card.should_exist()

        # Step 3: Add RAM component to EdgeDevice
        edge_device_card.open_accordion()
        edge_device_card.locator.locator("button[hx-get*='EdgeComponent']").click()
        page.locator("#sidePanelForm").wait_for(state="visible")
        side_panel.select_object_type("EdgeRAMComponent")
        side_panel.fill_field("EdgeRAMComponent_name", ram_component_name)
        side_panel.submit_and_wait_for_close()
        ram_card = model_builder.get_object_card("EdgeRAMComponent", ram_component_name)
        ram_card.should_exist()

        # Step 4: Create EdgeUsageJourney
        page.locator("#btn-add-edge-usage-journey").click()
        page.locator("#sidePanelForm").wait_for(state="visible")
        side_panel.fill_field("EdgeUsageJourney_name", edge_journey_name)
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("EdgeUsageJourney", edge_journey_name)

        # Step 5: Add EdgeFunction to journey
        edge_journey_card = model_builder.get_object_card("EdgeUsageJourney", edge_journey_name)
        edge_journey_card.click_add_step_button()
        side_panel.fill_field("EdgeFunction_name", edge_function_name)
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("EdgeFunction", edge_function_name)

        # Step 6: Add RecurrentEdgeDeviceNeed to EdgeFunction
        edge_function_card = model_builder.get_object_card("EdgeFunction", edge_function_name)
        edge_function_card.locator.locator("button[hx-get*='RecurrentEdgeDeviceNeed']").click()
        page.locator("#sidePanelForm").wait_for(state="visible")
        side_panel.select_option("edge_device", edge_device_name)
        # When selecting EdgeDevice (not EdgeComputer), RecurrentEdgeDeviceNeed is auto-selected
        side_panel.fill_field("RecurrentEdgeDeviceNeed_name", recurrent_need_name)
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("RecurrentEdgeDeviceNeed", recurrent_need_name)

        # Step 7: Add RecurrentEdgeComponentNeed for CPU
        edge_function_card.locator.locator(".accordion-header > .chevron-btn").first.click()
        recurrent_need_card = model_builder.get_object_card("RecurrentEdgeDeviceNeed", recurrent_need_name)
        recurrent_need_card.locator.locator("button[hx-get*='RecurrentEdgeComponentNeed']").click()
        page.locator("#sidePanelForm").wait_for(state="visible")
        side_panel.select_option("edge_component", cpu_component_name)
        side_panel.fill_field("RecurrentEdgeComponentNeed_name", cpu_need_name)
        page.locator("#RecurrentEdgeComponentNeed_recurrent_need").clear()
        page.locator("#RecurrentEdgeComponentNeed_recurrent_need").fill(cpu_need_value)
        # Verify unit was automatically set to cpu_core
        expect(page.locator("#RecurrentEdgeComponentNeed_recurrent_need__constant_unit")).to_have_value("cpu_core")
        side_panel.submit_and_wait_for_close()
        cpu_need_card = model_builder.get_object_card("RecurrentEdgeComponentNeed", cpu_need_name)
        cpu_need_card.should_exist()

        # Step 8: Add RecurrentEdgeComponentNeed for RAM
        recurrent_need_card.locator.locator(".accordion-header > .chevron-btn").first.click()
        recurrent_need_card.locator.locator("button[hx-get*='RecurrentEdgeComponentNeed']").click()
        page.locator("#sidePanelForm").wait_for(state="visible")
        side_panel.select_option("edge_component", ram_component_name)
        side_panel.fill_field("RecurrentEdgeComponentNeed_name", ram_need_name)
        page.locator("#RecurrentEdgeComponentNeed_recurrent_need").clear()
        page.locator("#RecurrentEdgeComponentNeed_recurrent_need").fill(ram_need_value)
        # Verify unit was automatically set to GB_ram
        expect(page.locator("#RecurrentEdgeComponentNeed_recurrent_need__constant_unit")).to_have_value("GB_ram")
        side_panel.submit_and_wait_for_close()
        ram_need_card = model_builder.get_object_card("RecurrentEdgeComponentNeed", ram_need_name)
        ram_need_card.should_exist()

        # Step 9: Verify unit changes dynamically when switching components
        recurrent_need_card.locator.locator(".accordion-header > .chevron-btn").first.click()
        recurrent_need_card.locator.locator("button[hx-get*='RecurrentEdgeComponentNeed']").click()
        page.locator("#sidePanelForm").wait_for(state="visible")
        side_panel.select_option("edge_component", cpu_component_name)
        expect(page.locator("#RecurrentEdgeComponentNeed_recurrent_need__constant_unit")).to_have_value("cpu_core")
        side_panel.select_option("edge_component", ram_component_name)
        expect(page.locator("#RecurrentEdgeComponentNeed_recurrent_need__constant_unit")).to_have_value("GB_ram")
