"""Tests for form behavior - unsaved changes, advanced options, source labels."""
from copy import deepcopy
import json
from urllib.parse import parse_qs, urlparse

import pytest
from efootprint.core.hardware.storage import Storage
from playwright.sync_api import expect

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.constants.units import u
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage
from tests.e2e.utils import EMPTY_SYSTEM_DICT


@pytest.mark.e2e
class TestUnsavedChangesWarning:
    """Tests for the unsaved changes warning modal."""

    def test_warns_when_closing_panel_with_unsaved_changes(self, empty_model_builder: ModelBuilderPage):
        """User should be warned when closing a form with unsaved changes."""
        model_builder = empty_model_builder
        page = model_builder.page

        # Open form and make changes
        model_builder.click_add_usage_journey()
        page.locator("#UsageJourney_name").click()
        page.locator("#UsageJourney_name").type("test name")

        # Try to close panel
        page.locator("#btn-close-side-panel").click()

        # Warning modal should appear (wait for Bootstrap modal animation)
        expect(page.locator("#unsavedModal.show")).to_be_visible()

        # Cancel to stay on form
        page.locator("#cancel-unsaved-modal").click()
        expect(page.locator("#unsavedModal.show")).not_to_be_visible()

    def test_warns_when_opening_new_panel_with_unsaved_changes(self, seeded_journey_model_builder: ModelBuilderPage):
        """User should be warned when opening another form with unsaved changes."""
        model_builder = seeded_journey_model_builder
        page = model_builder.page

        # Open form and make changes
        model_builder.click_add_usage_journey()
        page.locator("#UsageJourney_name").click()
        page.locator("#UsageJourney_name").type("test name")

        # Try to open another form by clicking on existing UJ
        default_uj_card = model_builder.get_object_card("UsageJourney", "My first usage journey")
        default_uj_card.locator.locator("button[id^='button-']").first.click()

        # Warning modal should appear (wait for Bootstrap modal animation)
        expect(page.locator("#unsavedModal.show")).to_be_visible()

        # Cancel to stay on form
        page.locator("#cancel-unsaved-modal").click()
        expect(page.locator("#unsavedModal.show")).not_to_be_visible()

    def test_pending_request_preserves_hx_vals(self, minimal_complete_model_builder: ModelBuilderPage):
        """Pending requests should keep hx-vals when user continues."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page
        side_panel = model_builder.side_panel

        step_card = model_builder.get_object_card("UsageJourneyStep", "Test Step")
        step_card.open_accordion()
        step_card.click_add_job_button()

        page.locator("#service_or_external_api").wait_for(state="attached")
        side_panel.select_option("service_or_external_api", "direct_server_call")
        side_panel.fill_field("Job_data_transferred", "15")

        server_card = model_builder.get_object_card("Server", "Test Server")
        add_service_button = server_card.locator.locator("button[id^='add-service-to']")
        hx_vals_raw = add_service_button.get_attribute("hx-vals")
        hx_vals = json.loads(hx_vals_raw or "{}")
        expected_parent_id = hx_vals.get("efootprint_id_of_parent_to_link_to")

        server_card.open_accordion()
        add_service_button.click()
        expect(page.locator("#unsavedModal.show")).to_be_visible()

        def is_expected_request(request):
            if "open-create-object-panel/Service" not in request.url:
                return False
            params = parse_qs(urlparse(request.url).query)
            return params.get("efootprint_id_of_parent_to_link_to", [None])[0] == expected_parent_id

        with page.expect_request(is_expected_request):
            page.locator("#continue-unsaved-modal").click()


@pytest.mark.e2e
class TestAdvancedOptions:
    """Tests for the advanced options toggle in forms."""

    def test_server_advanced_options_toggle_and_persist(self, empty_model_builder: ModelBuilderPage):
        """Advanced options should toggle visibility and values should persist."""
        model_builder = empty_model_builder
        side_panel = model_builder.side_panel
        page = model_builder.page

        server_name = "Test Server"

        # Create server with advanced option modified
        model_builder.click_add_server()
        side_panel.select_object_type("Server")
        side_panel.fill_field("Server_name", server_name)
        side_panel.fill_field("Server_average_carbon_intensity", "700")

        # Advanced section should be hidden by default
        expect(page.locator("#advanced-Server")).not_to_be_visible()

        # Toggle advanced options
        page.locator("#display-advanced-Server").click()
        expect(page.locator("#advanced-Server")).to_be_visible()

        # Modify an advanced field
        page.locator("#Server_power").clear()
        page.locator("#Server_power").fill("888")

        # Toggle closed and submit
        page.locator("#display-advanced-Server").click()
        expect(page.locator("#advanced-Server")).not_to_be_visible()
        side_panel.submit_and_wait_for_close()

        # Re-open and verify values persisted
        server_card = model_builder.get_object_card("Server", server_name)
        server_card.click_edit_button()

        expect(page.locator("#Server_average_carbon_intensity")).to_have_value("700")
        expect(page.locator("#advanced-Server")).not_to_be_visible()

        page.locator("#display-advanced-Server").click()
        expect(page.locator("#advanced-Server")).to_be_visible()
        expect(page.locator("#Server_power")).to_have_value("888")


@pytest.mark.e2e
class TestSourceLabels:
    """Tests for source labels displayed in forms."""

    def test_source_labels_display_in_usage_pattern_form(self, seeded_journey_model_builder: ModelBuilderPage):
        """Source labels should display correctly when creating and editing."""
        model_builder = seeded_journey_model_builder
        side_panel = model_builder.side_panel
        page = model_builder.page

        # Create usage pattern
        model_builder.click_add_usage_pattern()
        page.locator("#UsagePattern_hourly_usage_journey_starts__modeling_duration_value").fill("2")
        page.locator("#UsagePattern_hourly_usage_journey_starts__initial_volume").fill("1000")

        # Source label should show "user data"
        expect(page.locator("#source-UsagePattern_hourly_usage_journey_starts")).to_contain_text("Source: user data")

        side_panel.submit_and_wait_for_close()

        # Re-open and verify source label persists
        up_card = model_builder.get_object_card("UsagePattern", "Usage pattern 1")
        up_card.click_edit_button()

        expect(page.locator("#source-UsagePattern_hourly_usage_journey_starts")).to_contain_text("Source: user data")

        # Modify and verify source still shows
        page.locator("#UsagePattern_hourly_usage_journey_starts__net_growth_rate_in_percentage").fill("5")
        expect(page.locator("#source-UsagePattern_hourly_usage_journey_starts")).to_contain_text("Source: user data")


@pytest.fixture
def system_with_uj_no_steps(model_builder_page: ModelBuilderPage):
    """Create system with a UsageJourney but no UsageJourneySteps."""
    # Create a standalone UsageJourney with no steps
    uj = UsageJourney("Test E2E UJ", uj_steps=[])

    system_data = deepcopy(EMPTY_SYSTEM_DICT)
    system_data.update(system_to_json(uj, save_calculated_attributes=False))

    return load_system_dict_into_browser(model_builder_page, system_data)


@pytest.fixture
def system_with_uj_and_step(model_builder_page: ModelBuilderPage):
    """Create a system with a UsageJourney that already contains one UsageJourneyStep."""
    uj_step = UsageJourneyStep.from_defaults("Seeded step", jobs={})
    uj = UsageJourney("Seeded UJ", uj_steps=[uj_step])

    system_data = deepcopy(EMPTY_SYSTEM_DICT)
    system_data.update(system_to_json(uj, save_calculated_attributes=False))

    return load_system_dict_into_browser(model_builder_page, system_data)


@pytest.fixture
def system_with_custom_storage_unit(model_builder_page: ModelBuilderPage):
    """Create system with BoaviztaCloudServer with custom storage duration unit (month)."""
    # Create server with custom storage unit
    storage = Storage.ssd()
    server = BoaviztaCloudServer.from_defaults("cloud server test", storage=storage)

    # Set storage duration unit to 'month' (default is 'day')
    server.storage.data_storage_duration = SourceValue(5 * u.month)

    system_data = deepcopy(EMPTY_SYSTEM_DICT)
    system_data.update(system_to_json(server, save_calculated_attributes=False))

    return load_system_dict_into_browser(model_builder_page, system_data)


@pytest.mark.e2e
class TestFormFieldEnablement:
    """Tests that pickers with nothing to choose from are hidden rather than shown empty."""

    def test_uj_steps_picker_hidden_when_no_steps_available(self, system_with_uj_no_steps: ModelBuilderPage):
        """With no UsageJourneyStep to pick, the uj_steps picker is hidden in edit and create forms."""
        model_builder = system_with_uj_no_steps
        side_panel = model_builder.side_panel
        page = model_builder.page

        uj_steps_group = page.locator("#field-group-UsageJourney_uj_steps")

        # Editing the stepless UJ: nothing to pick -> picker hidden entirely
        uj_card = model_builder.get_object_card("UsageJourney", "Test E2E UJ")
        uj_card.click_edit_button()
        expect(uj_steps_group).to_be_hidden()
        side_panel.submit_and_wait_for_close()

        # Creating the first UJ likewise has nothing to pick -> picker hidden
        page.locator("#btn-add-usage-journey").click()
        expect(uj_steps_group).to_be_hidden()

    def test_uj_steps_picker_shown_when_steps_available(self, system_with_uj_and_step: ModelBuilderPage):
        """Once a UsageJourneyStep exists, the uj_steps picker is shown."""
        model_builder = system_with_uj_and_step
        page = model_builder.page

        uj_steps_group = page.locator("#field-group-UsageJourney_uj_steps")
        ujs_select = page.locator("#select-new-object-UsageJourney_uj_steps")

        # Editing the UJ that already contains the step: picker visible, but the only step is
        # already selected so there is nothing left to add -> select disabled
        uj_card = model_builder.get_object_card("UsageJourney", "Seeded UJ")
        uj_card.click_edit_button()
        expect(uj_steps_group).to_be_visible()
        expect(ujs_select).to_be_disabled()

        # Creating a NEW UJ: the existing step is selectable -> picker visible and enabled
        page.locator("#btn-add-usage-journey").click()
        expect(uj_steps_group).to_be_visible()
        expect(ujs_select).to_be_enabled()


@pytest.mark.e2e
class TestUnitsPersistence:
    """Tests that custom units persist when editing objects."""

    def test_storage_duration_unit_persists_on_edit(self, system_with_custom_storage_unit: ModelBuilderPage):
        """Storage duration unit should remain 'month' (not default 'day') after editing."""
        model_builder = system_with_custom_storage_unit
        side_panel = model_builder.side_panel
        page = model_builder.page

        # Open the server for editing
        server_card = model_builder.get_object_card("BoaviztaCloudServer", "cloud server test")
        server_card.click_edit_button()

        # Verify unit is 'month' (custom, not default 'year')
        storage_unit_select = page.locator("#Storage_data_storage_duration__unit")
        expect(storage_unit_select).to_have_value("month")

        # Change the value to 3
        storage_duration_input = page.locator("#Storage_data_storage_duration")
        storage_duration_input.clear()
        storage_duration_input.fill("3")

        # Submit
        side_panel.submit_and_wait_for_close()

        # Re-open the server
        server_card.click_edit_button()

        # Verify unit is still 'month' and value is '3'
        expect(storage_unit_select).to_have_value("month")
        expect(storage_duration_input).to_have_value("3")
