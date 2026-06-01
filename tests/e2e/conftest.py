"""E2E test configuration and fixtures.

This module provides Playwright fixtures integrated with Django.
It allows programmatic model creation using efootprint classes, which are then
loaded into the browser session for testing.

Usage:
    # Start Django server in one terminal:
    poetry run python manage.py runserver

    # Run E2E tests in another terminal:
    poetry run pytest tests/e2e/ --base-url http://localhost:8000
"""
import json
import tempfile
from copy import deepcopy
from pathlib import Path

import pytest
from efootprint.api_utils.system_to_json import system_to_json
from playwright.sync_api import Page

from tests.e2e.pages import ModelBuilderPage
from tests.e2e.utils import EMPTY_SYSTEM_DICT, add_only_update
from tests.fixtures.system_builders import build_seeded_journey_fragment


# Default base URL for E2E tests (Django dev server)
DEFAULT_BASE_URL = "http://localhost:8000"


def _attach_slow_request_logger(page: Page, threshold_ms: float = 500.0, test_name: str = "") -> None:
    """Log slow requests, real network errors, and a recent-request dump on nav timeouts.

    Disabled by default; set E2E_REQUEST_LOG=1 to enable when debugging flakiness.

    - `[SLOW  Nms]`   request completed but took >= threshold_ms
    - `[NETERR]`      genuine network error (not teardown-cancel ERR_ABORTED/ERR_FAILED)
    - `[PENDING]`     request still in flight when the test ended or a goto timed out
    - `[RECENT]`      rolling snapshot of the last ~40 requests (printed on nav timeout)
    """
    import os
    import time
    from collections import deque

    if os.environ.get("E2E_REQUEST_LOG", "0") != "1":
        return

    tag = f"[{test_name}] " if test_name else ""
    recent = deque(maxlen=40)       # (t_start, method, url, status)
    inflight: dict = {}             # url -> t_start

    def on_request(request):
        t = time.monotonic()
        inflight[request.url] = t
        recent.append((t, request.method, request.url, "start"))

    def on_finished(request):
        inflight.pop(request.url, None)
        try:
            timing = request.timing
            duration = timing.get("responseEnd", -1) if timing else -1
            recent.append((time.monotonic(), request.method, request.url, f"done {duration:.0f}ms"))
            if duration is not None and duration >= threshold_ms:
                print(f"{tag}[SLOW {duration:7.0f} ms] {request.method} {request.url}", flush=True)
        except Exception as exc:
            print(f"{tag}[timing err] {request.url}: {exc}", flush=True)

    def on_failed(request):
        inflight.pop(request.url, None)
        failure = (request.failure or "")
        recent.append((time.monotonic(), request.method, request.url, f"fail {failure}"))
        # ERR_ABORTED / ERR_FAILED are almost always teardown-cancel noise — skip them.
        if "ERR_ABORTED" in failure or "ERR_FAILED" in failure:
            return
        print(f"{tag}[NETERR] {request.method} {request.url} — {failure}", flush=True)

    def dump_recent(reason: str):
        now = time.monotonic()
        print(f"{tag}[RECENT] dump on {reason}:", flush=True)
        for t, method, url, status in list(recent)[-20:]:
            print(f"{tag}  t-{now - t:5.2f}s {method} {status} {url}", flush=True)
        for url, t in list(inflight.items()):
            print(f"{tag}[PENDING {now - t:5.2f}s] {url}", flush=True)

    page.on("request", on_request)
    page.on("requestfinished", on_finished)
    page.on("requestfailed", on_failed)
    # Expose the dump so the page-object goto can call it on TimeoutError.
    page._e2e_dump_recent = dump_recent  # type: ignore[attr-defined]


@pytest.fixture
def model_builder_page(page: Page, base_url: str, request) -> ModelBuilderPage:
    """Create a ModelBuilderPage instance configured for the test server.

    This fixture provides a page object ready for testing. The base_url
    is provided by pytest-base-url plugin and can be configured via:
    - --base-url command line option
    - base_url in pytest.ini
    - Environment variable PYTEST_BASE_URL
    """
    page.set_default_timeout(5000)  # 5 second default timeout for HTMX/UI updates under suite load
    _attach_slow_request_logger(page, test_name=request.node.name)
    server_url = base_url or DEFAULT_BASE_URL

    # Each Playwright context starts with empty localStorage, so the once-ever guided tour would
    # auto-run (and its overlay would block the canvas/side panel) in every suite. Mimic a returning
    # user by default — mark a test `onboarding_first_run` to exercise the first-run tour itself.
    if not request.node.get_closest_marker("onboarding_first_run"):
        page.add_init_script("try { localStorage.setItem('efootprint_onboarding_seen', 'true'); } catch (e) {}")

    # Override goto to use server URL for relative paths
    original_goto = page.goto

    def goto_with_base(url: str, **kwargs):
        if url.startswith("/"):
            url = f"{server_url}{url}"
        try:
            return original_goto(url, **kwargs)
        except Exception:
            dumper = getattr(page, "_e2e_dump_recent", None)
            if dumper:
                dumper(f"goto({url}) exception")
            raise

    page.goto = goto_with_base
    return ModelBuilderPage(page)


@pytest.fixture
def empty_model_builder(model_builder_page: ModelBuilderPage) -> ModelBuilderPage:
    """Navigate to the model builder with a fresh/default model.

    This starts from the home page and clicks 'Start modeling' to get
    the default initial model state.
    """
    model_builder_page.goto_home_and_start()
    return model_builder_page


@pytest.fixture
def edge_modeling_enabled(empty_model_builder: ModelBuilderPage) -> ModelBuilderPage:
    """Enable the edge-modeling toggle so edge-paradigm add-buttons are visible.

    A fresh session defaults to `edge-modeling-off`, which hides the edge add-buttons
    via CSS. Tests that need to click them must opt in via this fixture (typically
    applied to a class with `@pytest.mark.usefixtures("edge_modeling_enabled")`).
    """
    page = empty_model_builder.page
    page.evaluate("localStorage.setItem('efootprint.edgeModeling', 'on')")
    page.reload()
    # Reloading an empty model re-triggers the first-run picker; dismiss it so edge add-buttons are reachable.
    empty_model_builder.dismiss_template_picker_if_present()
    return empty_model_builder


@pytest.fixture
def minimal_complete_model_builder(minimal_system, model_builder_page) -> ModelBuilderPage:
    """Build a minimal complete system with all required objects connected.

    Creates: storage -> server -> job -> uj_step -> uj -> usage_pattern -> system
    This is useful when you need a valid system but don't care about specific objects.
    """
    minimal_system_dict = system_to_json(minimal_system, save_calculated_attributes=False)
    return load_system_dict_into_browser(model_builder_page, minimal_system_dict)


def load_system_dict_into_browser(model_builder_page: ModelBuilderPage, system_dict: dict) -> ModelBuilderPage:
    """Load a system dict into the browser session via JSON import.

    This takes a pre-built system dict (allowing orphaned objects like servers
    without jobs), writes it to a temp file, and imports it into the session.

    Args:
        model_builder_page: The page object to use
        system_dict: A system data dictionary (can include orphaned objects)

    Returns:
        The model_builder_page for chaining
    """
    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(system_dict, f)
        temp_path = f.name

    try:
        # Navigate to model builder first
        model_builder_page.goto()
        # Import the JSON file
        model_builder_page.import_json_file(temp_path)
    finally:
        # Clean up temp file
        Path(temp_path).unlink(missing_ok=True)

    return model_builder_page


def build_seeded_journey_dict() -> dict:
    """A minimal system dict containing one usage journey + step (see build_seeded_journey_fragment)."""
    system_data = deepcopy(EMPTY_SYSTEM_DICT)
    add_only_update(system_data, build_seeded_journey_fragment())
    return system_data


@pytest.fixture
def seeded_journey_model_builder(model_builder_page: ModelBuilderPage) -> ModelBuilderPage:
    """Model builder loaded with one usage journey + step (replaces old default seeding)."""
    return load_system_dict_into_browser(model_builder_page, build_seeded_journey_dict())


@pytest.fixture
def seeded_journey_json_path(tmp_path) -> str:
    """Path to a JSON file holding a one-journey system, for import-flow tests."""
    path = tmp_path / "seeded_journey.json"
    path.write_text(json.dumps(build_seeded_journey_dict()))
    return str(path)
