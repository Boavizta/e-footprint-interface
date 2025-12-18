"""Tests for toolbar features - import, export, reboot, system name."""
import os.path
from pathlib import Path

import pytest
from playwright.sync_api import expect

from efootprint.api_utils.system_to_json import system_to_json

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage
from tests.e2e.utils import click_and_wait_for_htmx, EMPTY_SYSTEM_DICT


@pytest.mark.e2e
class TestToolbarFeatures:
    """Tests for toolbar import/export/reboot features."""

    def test_reboot_clears_model(self, minimal_complete_model_builder: ModelBuilderPage):
        """Reboot should clear all objects and return to default state."""
        model_builder = minimal_complete_model_builder
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

    def test_change_system_name(self, minimal_complete_model_builder: ModelBuilderPage):
        """System name can be changed and persists after reload."""
        model_builder = minimal_complete_model_builder
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

    def test_import_json_replaces_existing_model(self, minimal_complete_model_builder: ModelBuilderPage):
        """Import JSON should replace existing model and reinitialize leader lines."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Verify initial model has objects
        model_builder.object_should_exist("UsagePattern", "Test Usage Pattern")
        model_builder.object_should_exist("UsageJourney", "Test Journey")

        # Set up spy for initLeaderLines function before submitting
        # This verifies that leader lines are redrawn after import
        page.evaluate("window.initLeaderLinesCalled = false")
        page.evaluate("""
                    const original = window.initLeaderLines;
                    window.initLeaderLines = function() {
                        window.initLeaderLinesCalled = true;
                        return original.apply(this, arguments);
                    };
                """)

        # Import the default model
        filedir = os.path.dirname(os.path.abspath(__file__))
        fixture_path = os.path.join(
            filedir, "..", "..", "model_builder", "domain", "reference_data", "default_system_data.json")
        model_builder.import_json_file(fixture_path)

        # Verify initLeaderLines was called
        leader_lines_called = page.evaluate("window.initLeaderLinesCalled")
        assert leader_lines_called, "initLeaderLines should have been called after import"

        # Verify objects from the imported model exist
        model_builder.object_should_exist("UsageJourney", "My first usage journey")

    def test_import_json_into_empty_model_adds_objects(self, model_builder_page: ModelBuilderPage):
        """Importing into an empty model should create objects from the JSON."""
        # Start from an empty system with no objects
        empty_model = load_system_dict_into_browser(model_builder_page, EMPTY_SYSTEM_DICT)
        page = empty_model.page

        # Verify no usage journeys or patterns exist initially
        expect(page.locator("div[id^='UsageJourney-']")).to_have_count(0)
        expect(page.locator("div[id^='UsagePattern-']")).to_have_count(0)

        # Import the default system
        fixture_path = Path(__file__).resolve().parents[2] / "model_builder" / "domain" / "reference_data" / "default_system_data.json"
        empty_model.import_json_file(str(fixture_path))

        # Objects from the imported model should now exist
        empty_model.object_should_exist("UsageJourney", "My first usage journey")

    def test_export_model_with_correct_filename_format(self, minimal_complete_model_builder: ModelBuilderPage):
        """Export should download JSON file with correct UTC timestamp filename."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Click export link and handle download
        with page.expect_download() as download_info:
            # Click the export link
            page.locator('a[href="download-json/"]').click()

        download = download_info.value

        # Get the suggested filename
        filename = download.suggested_filename

        # Verify filename format: YYYY-MM-DD HH_MM UTC system 1.e-f.json
        # We can't check exact timestamp, but we can verify the format
        import re
        from datetime import datetime

        # Pattern: YYYY-MM-DD HH_ followed by minutes, then UTC, system name, .e-f.json
        pattern = r'^\d{4}-\d{2}-\d{2} \d{2}_\d{2} UTC .+\.e-f\.json$'
        assert re.match(pattern, filename), f"Filename '{filename}' does not match expected format"

        # Verify it contains "UTC"
        assert "UTC" in filename, f"Filename should contain 'UTC': {filename}"

        # Verify it ends with .e-f.json
        assert filename.endswith(".e-f.json"), f"Filename should end with '.e-f.json': {filename}"

        # Verify year is reasonable (current year or within 1 year)
        current_year = datetime.now().year
        filename_year = int(filename[:4])
        assert abs(filename_year - current_year) <= 1, f"Year {filename_year} seems wrong (current: {current_year})"
