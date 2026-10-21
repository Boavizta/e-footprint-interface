"""Tests for model canvas interactions migrated from Cypress."""
import pytest
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
from playwright.sync_api import expect

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage
from tests.e2e.utils import add_only_update, wait_for_htmx_idle


@pytest.mark.e2e
class TestModelCanvas:
    """Model canvas behaviors (job creation buttons, accordion ordering)."""

    def test_edit_usage_journey_keeps_steps_visible(self, seeded_journey_model_builder: ModelBuilderPage):
        """Editing a usage journey without changes should keep its steps intact."""
        model_builder = seeded_journey_model_builder

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

    @pytest.mark.xfail(strict=True, reason="bug-fixes-2026-10 Task 2")
    def test_canvas_dict_count_edits_and_unlinks_log_no_console_error(self, minimal_system, model_builder_page):
        """Canvas count edits and unlinks never log an OOB-without-target error, whichever panel is open,
        and an open child panel still shows the count edited on the canvas."""
        device = EdgeDevice.from_defaults("Grouped Sensor", components=[])
        rack = EdgeDeviceGroup("Rack A", edge_device_counts={device: SourceValue(2 * u.dimensionless)})
        system_data = system_to_json(minimal_system, save_computed_state=False)
        add_only_update(system_data, system_to_json(rack, save_computed_state=False))
        page = model_builder_page.page
        # htmx logs only the bare event name; also log the OOB target it could not find.
        page.add_init_script("document.addEventListener('htmx:oobErrorNoTarget', e => console.error("
                             "'No OOB target: #' + e.detail.content.firstElementChild?.id))")
        model_builder = load_system_dict_into_browser(model_builder_page, system_data)

        console_errors: list[str] = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))
        errors_by_edit = {}

        def record(edit):
            wait_for_htmx_idle(page)
            errors_by_edit[edit] = console_errors.copy()
            console_errors.clear()

        step_card = model_builder.get_object_card("UsageJourneyStep", "Test Step")
        step_card.set_inline_count("3")
        record("step count, no panel")
        step_card.get_nested_object_card("Job", "Test Job").set_inline_count("2")
        record("job count, no panel")
        rack_card = model_builder.get_edge_device_group_card("Rack A")
        rack_card.open_accordion()
        device_card = rack_card.get_nested_object_card("EdgeDevice", "Grouped Sensor")
        device_card.set_inline_count("4")
        record("group entry count, no panel")

        step_card.click_edit_button()
        side_panel = model_builder.side_panel.should_be_visible()
        step_card.set_inline_count("5")
        expect(side_panel.panel.locator("[data-dict-membership-name='Test Journey'] input[name='count']")).to_have_value("5")
        record("step count, step panel open")
        device_card.set_inline_count("6")
        record("group entry count, step panel open")
        side_panel.close()

        device_card.click_unlink_button()
        record("group entry unlink, no panel")

        model_builder.add_model_by_duplication()
        with page.expect_response(lambda response: "update-dict-count" in response.url):
            model_builder.edit_first_relationship_count(7)
        record("step count, two models")

        assert not any(errors_by_edit.values()), f"Console errors per canvas edit: {errors_by_edit}"
