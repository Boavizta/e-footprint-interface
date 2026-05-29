"""E2E happy-path for the edge modeling toggle (latch + localStorage + add-button gating)."""
import pytest
from playwright.sync_api import expect

from tests.e2e.pages import ModelBuilderPage
from tests.e2e.utils import click_and_wait_for_htmx


LATCH_POPOVER_CONTENT = "This model contains edge objects. Remove them to turn edge modeling off."


@pytest.mark.e2e
class TestEdgeModelingToggle:
    def test_toggle_off_hides_edge_add_buttons(self, empty_model_builder: ModelBuilderPage):
        page = empty_model_builder.page

        # Default state on a fresh model: toggle unchecked + enabled, edge add-buttons hidden.
        page.evaluate("localStorage.removeItem('efootprint.edgeModeling')")
        page.reload()

        toggle = page.locator("#edge-modeling-toggle")
        expect(toggle).not_to_be_checked()
        expect(toggle).to_be_enabled()
        expect(page.locator("body.edge-modeling-off")).to_have_count(1)
        expect(page.locator("#btn-add-edge-device")).not_to_be_visible()

    def test_flipping_toggle_on_shows_edge_add_buttons_and_persists(self, empty_model_builder: ModelBuilderPage):
        page = empty_model_builder.page

        page.evaluate("localStorage.removeItem('efootprint.edgeModeling')")
        page.reload()

        page.locator("#edge-modeling-toggle").check()
        expect(page.locator("body.edge-modeling-on")).to_have_count(1)
        expect(page.locator("#btn-add-edge-device")).to_be_visible()

        assert page.evaluate("localStorage.getItem('efootprint.edgeModeling')") == "on"

    def test_creating_edge_device_latches_toggle(self, empty_model_builder: ModelBuilderPage):
        page = empty_model_builder.page
        side_panel = empty_model_builder.side_panel

        page.evaluate("localStorage.setItem('efootprint.edgeModeling', 'on')")
        page.reload()
        # Reloading an empty model re-triggers the first-run picker; dismiss it to reach the canvas.
        empty_model_builder.dismiss_template_picker_if_present()

        click_and_wait_for_htmx(page, page.locator("#btn-add-edge-device"))
        page.locator("#sidePanelForm").wait_for(state="visible")
        side_panel.fill_field("EdgeComputer_name", "Sensor")
        side_panel.submit_and_wait_for_close()

        toggle = page.locator("#edge-modeling-toggle")
        expect(toggle).to_be_disabled()
        expect(toggle).to_be_checked()
        latch_content = toggle.get_attribute("data-bs-content")
        assert latch_content == LATCH_POPOVER_CONTENT

    def test_localStorage_off_hides_edge_buttons_on_reload(self, empty_model_builder: ModelBuilderPage):
        page = empty_model_builder.page

        page.evaluate("localStorage.setItem('efootprint.edgeModeling', 'off')")
        page.reload()

        expect(page.locator("body.edge-modeling-off")).to_have_count(1)
        expect(page.locator("#btn-add-edge-device")).not_to_be_visible()
