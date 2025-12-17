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
from pathlib import Path

import pytest
from playwright.sync_api import Page

from tests.e2e.pages import ModelBuilderPage


# Default base URL for E2E tests (Django dev server)
DEFAULT_BASE_URL = "http://localhost:8000"


@pytest.fixture
def model_builder_page(page: Page, base_url: str) -> ModelBuilderPage:
    """Create a ModelBuilderPage instance configured for the test server.

    This fixture provides a page object ready for testing. The base_url
    is provided by pytest-base-url plugin and can be configured via:
    - --base-url command line option
    - base_url in pytest.ini
    - Environment variable PYTEST_BASE_URL
    """
    page.set_default_timeout(10000)  # 10 second default timeout
    server_url = base_url or DEFAULT_BASE_URL

    # Override goto to use server URL for relative paths
    original_goto = page.goto

    def goto_with_base(url: str, **kwargs):
        if url.startswith("/"):
            url = f"{server_url}{url}"
        return original_goto(url, **kwargs)

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
