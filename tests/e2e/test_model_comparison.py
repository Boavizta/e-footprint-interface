"""E2E for the two-model comparison builder (model-comparison Task 3).

The critical flow reserved for Playwright: duplicate the working model, edit the copy, refresh and
see both models + the active selection survive, then remove the copy to return to single-model mode.
This is the headline user-visible milestone, and it exercises the resident-canvas DOM in a real browser
(where a duplicate id would actually break HTMX/leaderlines, unlike a server-render assertion).
"""
import pytest
from playwright.sync_api import expect

from tests.e2e.utils import click_and_wait_for_htmx


@pytest.mark.e2e
class TestModelComparisonWorkspace:

    def test_duplicate_edit_refresh_and_remove(self, minimal_complete_model_builder):
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Single-model session: one tab, the +Add affordance, Compare disabled.
        expect(page.locator("#model-tab-strip")).to_be_visible()
        assert model_builder.active_model_tab_count() == 1
        expect(page.locator("#compare-tab")).to_be_disabled()

        # Add the second model by duplication — it becomes active (slot 1).
        model_builder.add_model_by_duplication()
        assert model_builder.active_model_tab_count() == 2
        assert model_builder.active_slot() == "1"
        expect(page.locator("[data-model-canvas='1']")).to_be_visible()
        expect(page.locator("[data-model-canvas='0']")).to_be_hidden()

        # Edit the copy independently: rename its system.
        new_name = "Edge caching variant"
        click_and_wait_for_htmx(page, page.locator("#btn-change-system-name"))
        page.locator("#sidePanel").wait_for(state="attached")
        page.locator("#name").clear()
        page.locator("#name").fill(new_name)
        model_builder.side_panel.submit_and_wait_for_close()
        expect(page.locator("#system-name")).to_contain_text(new_name)

        # Refresh: both models, their names, and the active selection survive the reload.
        page.reload()
        model_builder.canvas.wait_for(state="visible")
        assert model_builder.active_model_tab_count() == 2
        assert model_builder.active_slot() == "1"
        expect(page.locator("#system-name")).to_contain_text(new_name)
        expect(page.locator("[data-model-tab='1']")).to_contain_text(new_name)

        # Switch back to model A with no full reload (client-side canvas toggle).
        model_builder.switch_to_model(0)
        assert model_builder.active_slot() == "0"
        expect(page.locator("[data-model-canvas='0']")).to_be_visible()
        expect(page.locator("[data-model-canvas='1']")).to_be_hidden()

        # Switch to B and remove it — back to single-model mode with the +Add affordance restored.
        model_builder.switch_to_model(1)
        model_builder.remove_active_model()
        assert model_builder.active_model_tab_count() == 1
        expect(page.locator("#add-model-toggle")).to_be_visible()
