"""The journey of a first modeling started from a description, walked on the picker's AI entry."""
import pytest
from playwright.sync_api import expect

from comprehension_harness.python.declare import titled
from comprehension_harness.python.journey import journey, screen
from model_builder.application.ai_bootstrap.service import Completion
from tests.e2e.utils import handwritten_ai_answer

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True), pytest.mark.onboarding_first_run,
              pytest.mark.usefixtures("isolated_bootstrap")]
DESCRIPTION = "A recipe service: 20,000 monthly users browse and search recipes from their phones."


@journey("Start a modeling with AI",
         who="Someone opening the builder for the first time, with a system in mind and no model yet",
         wants="A first modeling of their system to correct, instead of an empty canvas to fill",
         now="2026-01-15T10:00:00Z")
class TestStartAModelingWithAI:
    @titled("describes a web system and gets a modeling to review")
    def test_describes_a_web_system(self, model_builder_page):
        builder, page = model_builder_page, model_builder_page.page
        page.goto("/model_builder/")
        builder.example_picker.wait_for(state="visible")
        screen(page, "example-picker", why="An empty modeling opens on the ways to start, the AI entry among the examples.")

        builder.start_ai_bootstrap("picker")
        screen(page, "description-panel", why="The description is asked for beside what it will cost and where it is sent.")

        builder.generate_ai_modeling(DESCRIPTION)
        screen(page, "generated-summary", why="The modeling is on the canvas, and the panel says what was generated from what.")

        builder.close_side_panel()
        screen(page, "generated-modeling", why="The summary is gone with its panel: what remains is a modeling like any other.")

    @titled("asks for edge devices too")
    def test_asks_for_edge_devices(self, model_builder_page, isolated_bootstrap):
        builder, page = model_builder_page, model_builder_page.page
        isolated_bootstrap.return_value = Completion(handwritten_ai_answer("04_ev_charging"), 5000, 2000, latency_s=15)
        page.goto("/model_builder/")
        builder.example_picker.wait_for(state="visible")
        builder.start_ai_bootstrap("picker")
        page.get_by_label("Web + edge").check()
        expect(page.locator('[data-ai-bootstrap-panel="input"] [data-ai-scope="web_edge"]').first).to_be_visible()
        screen(page, "description-panel", why="Web + edge shows its own guidance, model, cost and impact.")

        builder.generate_ai_modeling(DESCRIPTION)
        screen(page, "generated-summary", why="The edge devices are on the canvas, Edge modeling switched on for them.")
