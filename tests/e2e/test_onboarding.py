"""E2E for the first-run onboarding flow: empty-model picker, template load, re-open paths,
and the guided tour (auto-run, replay, non-blocking help step, IoT edge latch).

Covers the critical first-run journey only (testing.md "minimal, non-redundant"): entering
an empty model shows the picker; picking a card loads a working system; the toolbar Help
menu re-opens the picker; the guided tour auto-runs once, replays from the help menu, opens
the help drawer non-blockingly, and the IoT template lands with the edge toggle latched on.
"""
import pytest
from playwright.sync_api import expect

from tests.e2e.pages import ModelBuilderPage
from tests.e2e.utils import click_and_wait_for_htmx


@pytest.mark.e2e
@pytest.mark.onboarding_first_run
class TestOnboardingPicker:
    def test_empty_model_shows_picker_and_loading_a_template_swaps_the_canvas(
            self, model_builder_page: ModelBuilderPage):
        page = model_builder_page.page

        # Entering the builder with an empty model meets the user with the picker (raw nav,
        # bypassing the page object's auto-dismiss).
        page.goto("/model_builder/")
        expect(model_builder_page.template_picker).to_be_visible()
        for template_id in ("ecommerce", "ai_chatbot", "iot_industrial", "scratch"):
            expect(model_builder_page.template_picker.locator(f"[data-template-id='{template_id}']")).to_be_visible()

        # Picking the e-commerce template loads its working system onto the canvas.
        model_builder_page.pick_template("ecommerce")
        expect(page.locator("[id^='UsageJourney-']").first).to_be_visible()

    def test_start_from_scratch_loads_an_empty_canvas(self, model_builder_page: ModelBuilderPage):
        page = model_builder_page.page
        page.goto("/model_builder/")
        expect(model_builder_page.template_picker).to_be_visible()

        model_builder_page.pick_template("scratch")
        # Empty baseline: no object cards on the canvas.
        expect(page.locator("[id^='UsageJourney-']")).to_have_count(0)
        expect(page.locator("[id^='Server-']")).to_have_count(0)

    def test_help_menu_reopens_picker_over_a_loaded_model(self, model_builder_page: ModelBuilderPage):
        page = model_builder_page.page
        page.goto("/model_builder/")
        model_builder_page.pick_template("ecommerce")
        expect(page.locator("[id^='UsageJourney-']").first).to_be_visible()

        # Re-open the picker mid-session without losing the current model.
        model_builder_page.open_template_picker_from_help_menu()
        expect(model_builder_page.template_picker).to_be_visible()
        model_builder_page.dismiss_template_picker_if_present()
        expect(page.locator("[id^='UsageJourney-']").first).to_be_visible()

    def test_picking_a_template_over_a_loaded_model_confirms_first(self, model_builder_page: ModelBuilderPage):
        """Regression: replacing a loaded model from the re-opened picker must confirm first.

        The picker is server-rendered once; its replace-confirmation is decided client-side at
        click time from the live DOM, so it stays correct whether the picker overlays an empty
        canvas (no prompt) or a populated one (prompt).
        """
        page = model_builder_page.page
        page.goto("/model_builder/")
        model_builder_page.pick_template("ecommerce")
        expect(page.locator("[id^='UsageJourney-']").first).to_be_visible()

        # Re-open the picker over the now-loaded model and pick a different template.
        model_builder_page.open_template_picker_from_help_menu()

        dialogs = []

        def accept(dialog):
            dialogs.append(dialog.message)
            dialog.accept()

        page.on("dialog", accept)
        click_and_wait_for_htmx(
            page, model_builder_page.template_picker.locator("[data-template-id='ai_chatbot']"))

        assert dialogs, "Replacing a loaded model from the picker should ask for confirmation"
        expect(model_builder_page.template_picker).to_have_count(0)


@pytest.mark.e2e
@pytest.mark.onboarding_first_run
class TestOnboardingTour:
    def test_data_tour_target_anchors_are_present(self, model_builder_page: ModelBuilderPage):
        page = model_builder_page.page
        page.goto("/model_builder/")
        model_builder_page.pick_template("ecommerce")
        for target in ("usage-journeys", "infrastructure", "edge-modeling", "usage-patterns", "results", "help-menu"):
            expect(page.locator(f"[data-tour-target='{target}']")).to_have_count(1)

    def test_tour_auto_runs_after_a_template_loads(self, model_builder_page: ModelBuilderPage):
        page = model_builder_page.page
        # Raw nav so the first-run flag is fresh (each Playwright context has clean localStorage).
        page.goto("/model_builder/")
        expect(model_builder_page.tour_popover).not_to_be_visible()

        # Picking a template dismisses the picker; the tour then auto-runs once ever.
        model_builder_page.pick_template("ecommerce")
        expect(model_builder_page.tour_popover).to_be_visible()

    def test_tour_does_not_re_run_on_a_returning_visit(self, model_builder_page: ModelBuilderPage):
        page = model_builder_page.page
        page.goto("/model_builder/")
        model_builder_page.pick_template("ecommerce")
        expect(model_builder_page.tour_popover).to_be_visible()

        # The flag is now set; re-entering the (now non-empty) builder must not re-run the tour.
        page.goto("/model_builder/")
        expect(page.locator("[id^='UsageJourney-']").first).to_be_visible()
        expect(model_builder_page.tour_popover).not_to_be_visible()

    def test_replay_from_help_menu_reopens_the_tour(self, model_builder_page: ModelBuilderPage):
        page = model_builder_page.page
        page.goto("/model_builder/")
        model_builder_page.pick_template("ecommerce")
        # Dismiss the auto-run tour, then replay it from the help menu.
        page.locator(".driver-popover-close-btn").click()
        expect(model_builder_page.tour_popover).not_to_be_visible()

        model_builder_page.replay_tour_from_help_menu()
        expect(model_builder_page.tour_popover).to_be_visible()

    def test_help_step_opens_drawer_and_drawer_stays_clickable(self, model_builder_page: ModelBuilderPage):
        page = model_builder_page.page
        page.goto("/model_builder/")
        model_builder_page.pick_template("ecommerce")
        expect(model_builder_page.tour_popover).to_be_visible()

        # Advance to the step that opens the help drawer while the tour stays open.
        model_builder_page.advance_tour_to_help_step()
        help_drawer = page.locator("#helpDrawer")
        expect(help_drawer).to_be_visible()
        expect(model_builder_page.tour_popover).to_be_visible()

        # Non-blocking: the drawer's close button is interactable while the tour runs.
        page.locator("#btn-close-help-drawer").click()
        expect(help_drawer).not_to_be_visible()

    def test_iot_template_lands_with_edge_toggle_latched_on(self, model_builder_page: ModelBuilderPage):
        page = model_builder_page.page
        page.goto("/model_builder/")
        model_builder_page.pick_template("iot_industrial")

        toggle = page.locator("#edge-modeling-toggle")
        expect(toggle).to_be_checked()
        expect(toggle).to_be_disabled()
        expect(page.locator("body.edge-modeling-on")).to_have_count(1)
