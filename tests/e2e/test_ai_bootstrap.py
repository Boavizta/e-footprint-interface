"""Real bootstrap navigation and persistence, with inference isolated in process."""
import json
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest
from django.conf import settings as django_settings
from django.core.cache import caches
from playwright.sync_api import expect, sync_playwright

from model_builder.adapters.views import views_ai_bootstrap
from model_builder.application.ai_bootstrap.service import Completion
from comprehension_harness.python.declare import titled
from tests.e2e.utils import click_and_wait_for_htmx, wait_for_htmx_idle

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]
EDGE_ANSWER = (Path(django_settings.BASE_DIR) / "ai_sandbox/cases/_handwritten_04_ev_charging.json").read_text()
DESCRIPTION = 'Recipe service <script>alert("prompt")</script> & monthly users'


@pytest.fixture
def page(transactional_db, browser_name, browser_type_launch_args):
    # Keep Playwright's synchronous event loop inside the database fixture's lifetime.
    with sync_playwright() as playwright:
        browser = getattr(playwright, browser_name).launch(**browser_type_launch_args)
        context = browser.new_context()
        page = context.new_page()
        yield page
        context.close()
        browser.close()


@pytest.fixture(autouse=True)
def isolated_bootstrap(settings, monkeypatch):
    monkeypatch.setenv("USE_BOAVIZTAPI_PACKAGE", "1")
    settings.AI_BOOTSTRAP_ENABLED = True
    settings.MISTRAL_API_KEY = "dummy-offline-key"
    settings.STORAGES = {**settings.STORAGES, "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
    # LocMem is shared by the request thread and test, with separate locations for every test and alias.
    prefix = f"bootstrap-{uuid4()}"
    settings.CACHES = {alias: {"BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                              "LOCATION": f"{prefix}-{alias}"} for alias in ("default", "redis", "postgres")}
    answer = (Path(django_settings.BASE_DIR) / "ai_sandbox/cases/_handwritten_01_recipe_app.json").read_text()
    provider = Mock(return_value=Completion(answer, 5000, 800, latency_s=1.5))
    monkeypatch.setattr(views_ai_bootstrap, "complete_mistral", provider)
    monkeypatch.setattr(views_ai_bootstrap, "estimate_call", lambda completion: {
        "cost_usd": 0.001, "cache_discount_unknown": True, "rate_card_date": "2026-11-09", "impact_kg": None})
    yield provider
    for alias in settings.CACHES:
        caches[alias].clear()


@pytest.fixture(scope="session")
def base_url(live_server):
    return live_server.url


def assert_results_closed(page):
    expect(page.locator("#result-block")).to_be_empty()
    expect(page.locator("#btn-open-panel-result")).to_be_visible()


def edit_generated_server(builder):
    page = builder.page
    click_and_wait_for_htmx(page, page.locator("#server-list button[hx-get*='open-edit-object-panel']").first)
    expect(builder.ai_bootstrap_summary).to_have_count(0)
    page.locator("#sidePanel input[id$='_name']").first.fill("Reviewed server")
    builder.side_panel.submit_and_wait_for_close()
    click_and_wait_for_htmx(page, page.locator("#server-list button[hx-get*='open-edit-object-panel']").first)
    expect(page.locator("#sidePanel input[id$='_name']").first).to_have_value("Reviewed server")


def test_toolbar_cancel_then_generate_locks_and_installs(minimal_complete_model_builder, isolated_bootstrap):
    builder = minimal_complete_model_builder
    page = builder.page
    before = page.locator("[data-model-canvas='0'] .model-builder-card").count()
    starts = []
    page.on("request", lambda request: starts.append(request) if "start-ai-bootstrap" in request.url else None)
    builder.open_modeling_actions()
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.locator('[data-ai-bootstrap-entry="toolbar"]').click()
    assert not starts
    assert page.locator("[data-model-canvas='0'] .model-builder-card").count() == before
    page.once("dialog", lambda dialog: dialog.accept())
    builder.start_ai_bootstrap()
    expect(page.locator("[data-model-canvas] .model-builder-card")).to_have_count(0)
    assert_results_closed(page)
    pending = []
    page.route("**/generate-ai-bootstrap/", lambda route: pending.append(route))
    page.locator("#ai-description").fill(DESCRIPTION)
    with page.expect_request("**/generate-ai-bootstrap/"):
        page.locator("#btn-submit-form").click()
    for selector in ("#btn-submit-form", "#btn-close-side-panel", "#modeling-actions-toggle",
                     '[data-action="modeling-view"]', '[data-action="simplified-view"]'):
        expect(page.locator(selector)).to_be_disabled()
    # Native activation of the disabled button cannot issue a duplicate request.
    page.locator("#btn-submit-form").evaluate("button => button.click()")
    assert len(pending) == 1
    assert isolated_bootstrap.call_count == 0
    with page.expect_response("**/generate-ai-bootstrap/"):
        pending.pop().continue_()
    expect(builder.ai_bootstrap_summary).to_be_visible()
    wait_for_htmx_idle(page)
    assert isolated_bootstrap.call_count == 1
    assert_results_closed(page)
    details = builder.ai_bootstrap_summary.locator("details")
    expect(details).not_to_have_attribute("open", "")
    expect(details.locator("script")).to_have_count(0)
    details.locator("summary").click()
    expect(details.locator("pre")).to_have_text(DESCRIPTION)
    selected = details.locator("pre").evaluate("""element => {
        const range = document.createRange();
        range.selectNodeContents(element);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        return selection.toString();
    }""")
    assert selected == DESCRIPTION
    builder.close_side_panel()
    expect(builder.ai_bootstrap_summary).to_have_count(0)
    edit_generated_server(builder)


@pytest.mark.parametrize("disposal", ["edit", "reload"])
def test_summary_is_response_local_and_graph_remains_editable(empty_model_builder, disposal):
    builder = empty_model_builder
    builder.start_ai_bootstrap().generate_ai_modeling(DESCRIPTION)
    if disposal == "reload":
        builder.page.reload()
        wait_for_htmx_idle(builder.page)
        expect(builder.ai_bootstrap_summary).to_have_count(0)
        expect(builder.page.locator("#ai-description")).to_have_count(0)
    edit_generated_server(builder)


@pytest.mark.onboarding_first_run
def test_picker_cancellation_and_first_run_suppression(model_builder_page):
    builder = model_builder_page
    page = builder.page
    page.goto("/model_builder/")
    builder.example_picker.wait_for(state="visible")
    builder.start_ai_bootstrap("picker")
    expect(builder.example_picker).to_have_count(0)
    assert page.evaluate("localStorage.getItem('efootprint_onboarding_seen')") == "true"
    expect(builder.tour_popover).to_have_count(0)
    builder.generate_ai_modeling(DESCRIPTION)
    expect(builder.tour_popover).to_have_count(0)
    builder.open_example_picker_from_help_menu()
    before = page.locator("[data-model-canvas] .model-builder-card").count()
    starts = []
    page.on("request", lambda request: starts.append(request) if "start-ai-bootstrap" in request.url else None)
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.locator('[data-ai-bootstrap-entry="picker"]').click()
    expect(builder.example_picker).to_be_visible()
    assert page.locator("[data-model-canvas] .model-builder-card").count() == before
    assert not starts
    page.once("dialog", lambda dialog: dialog.accept())
    builder.start_ai_bootstrap("picker")
    expect(builder.example_picker).to_have_count(0)
    builder.close_side_panel().replay_tour_from_help_menu()
    expect(builder.tour_popover).to_be_visible()


def test_view_buttons_stay_in_place_and_hidden_canvas_still_confirms(minimal_complete_model_builder):
    builder = minimal_complete_model_builder
    page = builder.page
    buttons = [page.locator(f'[data-action="{view}-view"]') for view in ("modeling", "simplified")]
    boxes = [button.bounding_box() for button in buttons]
    builder.open_simplified_inputs()
    for button, box in zip(buttons, boxes):
        after = button.bounding_box()
        assert after == pytest.approx(box, abs=0.5)
    expect(buttons[1]).to_have_attribute("aria-pressed", "true")
    builder.open_modeling_actions()
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.locator('[data-ai-bootstrap-entry="toolbar"]').click()
    expect(page.locator("body")).to_have_attribute("data-base-view", "simplified")
    expect(page.locator("[data-ai-bootstrap-panel]")).to_have_count(0)
    page.once("dialog", lambda dialog: dialog.accept())
    builder.start_ai_bootstrap()
    expect(page.locator("body")).to_have_attribute("data-base-view", "modeling")
    expect(buttons[0]).to_have_attribute("aria-pressed", "true")


@titled("ai-bootstrap-edge#scope-choice: checking Web + edge shows its guidance, model, cost and impact, and keeps the "
        "description typed [scope-disclosed]")
def test_scope_choice_switches_guidance_and_disclosure(empty_model_builder):
    builder = empty_model_builder
    page = builder.page
    builder.start_ai_bootstrap()
    panel = page.locator('[data-ai-bootstrap-panel="input"]')
    web, web_edge = panel.locator('[data-ai-scope="web"]'), panel.locator('[data-ai-scope="web_edge"]')
    expect(page.get_by_label("Web only")).to_be_checked()
    expect(web.last).to_contain_text("USD 0.0012")
    for index in range(web.count()):
        expect(web.nth(index)).to_be_visible()
        expect(web_edge.nth(index)).to_be_hidden()
    page.locator("#ai-description").fill(DESCRIPTION)

    page.get_by_label("Web + edge").check()

    for index in range(web.count()):
        expect(web.nth(index)).to_be_hidden()
        expect(web_edge.nth(index)).to_be_visible()
    expect(web_edge.first).to_contain_text("Which devices does your system deploy")
    for disclosed in ("zai-glm-5-3-flash", "USD 0.0015", "below 1 g CO2-eq"):
        expect(web_edge.last).to_contain_text(disclosed)
    expect(page.locator("#ai-description")).to_have_value(DESCRIPTION)


@titled("ai-bootstrap-edge#scope-choice: with Edge modeling on, Start with AI opens on Web + edge, showing its "
        "guidance and disclosure alone [edge-modeling-preselects]")
def test_start_opens_on_web_edge_when_edge_modeling_is_on(edge_modeling_enabled):
    builder = edge_modeling_enabled
    page = builder.page
    builder.start_ai_bootstrap()
    panel = page.locator('[data-ai-bootstrap-panel="input"]')
    web, web_edge = panel.locator('[data-ai-scope="web"]'), panel.locator('[data-ai-scope="web_edge"]')

    expect(page.get_by_label("Web + edge")).to_be_checked()
    for index in range(web.count()):
        expect(web.nth(index)).to_be_hidden()
        expect(web_edge.nth(index)).to_be_visible()
    expect(web_edge.last).to_contain_text("USD 0.0015")


@titled("ai-bootstrap-edge#scope-choice: Web + edge generation shows edge objects; a web usage cut to 10 years is "
        "listed and keeps its period")
def test_web_edge_generation_keeps_a_cut_web_usage_period(empty_model_builder, isolated_bootstrap):
    builder = empty_model_builder
    page = builder.page
    # 3,000 a week, 428.57 a day, opens on the editor's whole-number step: 429 a day saves unchanged.
    answer = json.loads(EDGE_ANSWER)
    answer["usage_patterns"][0]["volume"] = {"value": 3000, "per": "week"}
    isolated_bootstrap.return_value = Completion(json.dumps(answer), 5000, 2000, latency_s=15)
    builder.start_ai_bootstrap()
    page.get_by_label("Web + edge").check()

    builder.generate_ai_modeling(DESCRIPTION)

    expect(page.locator("#edge-modeling-toggle")).to_be_checked()
    expect(page.locator("#edge-devices-list").get_by_text("Station controller")).to_be_visible()
    expect(builder.ai_bootstrap_summary).to_contain_text(
        "usage period: Operations team: 2024-01-01 to 2035-12-28 → 2024-01-01 to 2033-12-28 "
        "(Growth projection holds 10 years at most)")
    builder.close_side_panel()
    period = {"start_date": "2024-01-01", "modeling_duration_value": "10", "modeling_duration_unit": "year"}

    def opened_inputs():
        click_and_wait_for_htmx(page, page.locator("#up-list button[hx-get*='open-edit-object-panel']").first)
        return {key: page.locator(f"#UsagePattern_hourly_occurrences__{key}").input_value()
                for key in [*period, "initial_volume"]}

    opened = opened_inputs()
    assert {key: opened[key] for key in period} == period and opened["initial_volume"] == "429"
    builder.side_panel.submit_and_wait_for_close()
    assert opened_inputs() == opened
