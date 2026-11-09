"""Real bootstrap navigation and persistence, with inference isolated in process."""
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest
from django.conf import settings as django_settings
from django.core.cache import caches
from playwright.sync_api import expect, sync_playwright

from model_builder.adapters.views import views_ai_bootstrap
from model_builder.application.ai_bootstrap.service import Completion
from tests.e2e.utils import click_and_wait_for_htmx, wait_for_htmx_idle

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]
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
