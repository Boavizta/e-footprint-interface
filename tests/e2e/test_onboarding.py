"""E2E for the first-run onboarding flow: empty-model picker, template load, re-open paths.

Covers the critical first-run journey only (testing.md "minimal, non-redundant"): entering
an empty model shows the picker; picking a card loads a working system; the home "Browse
templates" CTA and the toolbar Help menu both re-open the picker. The guided-tour and
IoT-edge-latch assertions land in Step 6 Task 3.
"""
import pytest
from playwright.sync_api import expect

from tests.e2e.pages import ModelBuilderPage


@pytest.mark.e2e
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

    def test_home_browse_templates_cta_opens_the_picker(self, model_builder_page: ModelBuilderPage):
        page = model_builder_page.page
        page.goto("/")
        page.locator("#btn-browse-templates").click()
        expect(model_builder_page.template_picker).to_be_visible()

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
