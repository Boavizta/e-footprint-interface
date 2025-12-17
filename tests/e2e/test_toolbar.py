"""Tests for toolbar features - import, export, reboot, system name."""
import pytest
from playwright.sync_api import expect

from efootprint.api_utils.system_to_json import system_to_json

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage
from tests.e2e.utils import click_and_wait_for_htmx
from tests.fixtures import build_minimal_system


@pytest.fixture
def system_dict_complete():
    """Create a complete system dict."""
    system = build_minimal_system("Test System")
    return system_to_json(system, save_calculated_attributes=False)


@pytest.fixture
def complete_system_in_browser(model_builder_page: ModelBuilderPage, system_dict_complete):
    """Load complete system into browser."""
    return load_system_dict_into_browser(model_builder_page, system_dict_complete)


@pytest.mark.e2e
class TestToolbarFeatures:
    """Tests for toolbar import/export/reboot features."""

    def test_reboot_clears_model(self, complete_system_in_browser: ModelBuilderPage):
        """Reboot should clear all objects and return to default state."""
        model_builder = complete_system_in_browser
        page = model_builder.page

        # Verify we have objects from the loaded system
        model_builder.object_should_exist("UsagePattern", "Test Usage Pattern")
        model_builder.object_should_exist("UsageJourney", "Test Journey")

        # Click reboot
        with page.expect_response(lambda r: "reboot" in r.url):
            page.locator("#btn-reboot-modeling").click()

        # Verify model is reset to default state
        expect(page.locator("div").filter(has_text="Test Usage Pattern")).not_to_be_visible()
        expect(page.locator("div").filter(has_text="Test Journey")).not_to_be_visible()

        # Default UJ should exist
        expect(page.locator("div").filter(has_text="My first usage journey").first).to_be_visible()

    def test_change_system_name(self, complete_system_in_browser: ModelBuilderPage):
        """System name can be changed and persists after reload."""
        model_builder = complete_system_in_browser
        side_panel = model_builder.side_panel
        page = model_builder.page

        new_name = "My Custom System Name"

        # Click change name button

        click_and_wait_for_htmx(page, page.locator("#btn-change-system-name"))
        page.locator("#sidePanel").wait_for(state="attached")

        # Change the name
        page.locator("#name").clear()
        page.locator("#name").fill(new_name)
        side_panel.submit_and_wait_for_close()

        # Verify name changed
        expect(page.locator("#system-name")).to_contain_text(new_name)

        # Reload and verify name persists
        page.reload()
        page.locator("#model-canva").wait_for(state="visible")
        expect(page.locator("#system-name")).to_contain_text(new_name)
