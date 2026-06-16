"""Tests for toolbar features - import, export, reboot, system name."""
import pytest
from playwright.sync_api import expect

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage, card_id_selector
from tests.e2e.utils import click_and_wait_for_htmx, EMPTY_SYSTEM_DICT


@pytest.mark.e2e
class TestToolbarFeatures:
    """Tests for toolbar import/export/reboot features."""

    def test_reboot_clears_model(self, minimal_complete_model_builder: ModelBuilderPage):
        """Reboot should clear all objects and return to the empty default state."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Verify we have objects from the loaded system
        model_builder.object_should_exist("UsagePattern", "Test Usage Pattern")
        model_builder.object_should_exist("UsageJourney", "Test Journey")

        # Reset (confirming the discard of the populated model)
        model_builder.reset_to_default()

        # Verify model is reset to the empty default state (Step 6 slimmed the default to an empty System)
        expect(page.locator("div").filter(has_text="Test Usage Pattern")).not_to_be_visible()
        expect(page.locator("div").filter(has_text="Test Journey")).not_to_be_visible()
        expect(page.locator(card_id_selector("UsageJourney"))).to_have_count(0)
        expect(page.locator(card_id_selector("UsagePattern"))).to_have_count(0)

    def test_reboot_confirms_after_adding_to_initially_empty_model(self, empty_model_builder: ModelBuilderPage):
        """Regression: reboot must confirm once the model has content, even when the page loaded empty.

        The toolbar (and its reboot button) is only re-rendered on full-page swaps, never when an
        object is added via a partial swap. A server-rendered ``hx-confirm`` would therefore stay
        frozen at its empty-model value and reboot silently. The confirmation is decided client-side
        at click time from the live DOM instead.
        """
        model_builder = empty_model_builder
        page = model_builder.page

        # Add an object via a partial swap (does not re-render the toolbar).
        model_builder.click_add_usage_journey()
        model_builder.side_panel.fill_field("UsageJourney_name", "UJ for reboot confirm")
        model_builder.side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("UsageJourney", "UJ for reboot confirm")

        # Rebooting now must prompt for confirmation.
        dialogs = []

        def accept(dialog):
            dialogs.append(dialog.message)
            dialog.accept()

        page.on("dialog", accept)
        click_and_wait_for_htmx(page, page.locator("#btn-reboot-modeling"))

        assert dialogs, "Reboot should ask for confirmation once the model has content"

    def test_reboot_on_empty_model_does_not_confirm(self, empty_model_builder: ModelBuilderPage):
        """Rebooting an already-empty model has nothing to discard, so it must not prompt."""
        model_builder = empty_model_builder
        page = model_builder.page

        dialogs = []

        def accept(dialog):
            dialogs.append(dialog.message)
            dialog.accept()

        page.on("dialog", accept)
        click_and_wait_for_htmx(page, page.locator("#btn-reboot-modeling"))

        assert not dialogs, "Rebooting an empty model should not prompt for confirmation"

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
        page.locator("[data-model-canvas]:not(.d-none)").wait_for(state="visible")
        expect(page.locator("#system-name")).to_contain_text(new_name)

    def test_import_json_replaces_existing_model(
            self, minimal_complete_model_builder: ModelBuilderPage, seeded_journey_json_path: str):
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

        # Import a system containing a usage journey
        model_builder.import_json_file(seeded_journey_json_path)

        # Verify initLeaderLines was called
        leader_lines_called = page.evaluate("window.initLeaderLinesCalled")
        assert leader_lines_called, "initLeaderLines should have been called after import"

        # Verify objects from the imported model exist
        model_builder.object_should_exist("UsageJourney", "My first usage journey")

    def test_import_json_into_empty_model_adds_objects(
            self, model_builder_page: ModelBuilderPage, seeded_journey_json_path: str):
        """Importing into an empty model should create objects from the JSON."""
        # Start from an empty system with no objects
        empty_model = load_system_dict_into_browser(model_builder_page, EMPTY_SYSTEM_DICT)
        page = empty_model.page

        # Verify no usage journeys or patterns exist initially
        expect(page.locator(card_id_selector("UsageJourney"))).to_have_count(0)
        expect(page.locator(card_id_selector("UsagePattern"))).to_have_count(0)

        # Import a system containing a usage journey
        empty_model.import_json_file(seeded_journey_json_path)

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
