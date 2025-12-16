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
from efootprint.api_utils.system_to_json import system_to_json

from tests.e2e.pages import ModelBuilderPage
from tests.fixtures import build_minimal_system


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


def load_system_into_browser(model_builder_page: ModelBuilderPage, system) -> ModelBuilderPage:
    """Load an efootprint System into the browser session via JSON import.

    This converts the system to JSON, writes it to a temp file, and uses
    the import functionality to load it into the session.

    Args:
        model_builder_page: The page object to use
        system: An efootprint System instance

    Returns:
        The model_builder_page for chaining
    """
    # Serialize system to JSON
    system_data = system_to_json(system, save_calculated_attributes=True)

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(system_data, f)
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


@pytest.fixture
def minimal_system_in_browser(model_builder_page: ModelBuilderPage, minimal_system) -> ModelBuilderPage:
    """Load the minimal test system into the browser.

    This fixture combines the minimal_system fixture (from conftest.py)
    with the browser, giving you a ready-to-test model builder with
    a complete minimal system loaded.

    The minimal system includes:
    - Storage -> Server -> Job -> UJ Step -> UJ -> Usage Pattern
    """
    return load_system_into_browser(model_builder_page, minimal_system)


# --- Fixtures for specific test scenarios ---

@pytest.fixture
def system_without_jobs():
    """Create a system with server but no jobs (for job creation tests)."""
    from efootprint.core.hardware.storage import Storage
    from efootprint.core.hardware.server import Server
    from efootprint.core.usage.usage_journey import UsageJourney
    from efootprint.core.usage.usage_journey_step import UsageJourneyStep
    from efootprint.core.system import System

    storage = Storage.from_defaults("Test Storage")
    server = Server.from_defaults("Test Server", storage=storage)
    uj_step = UsageJourneyStep.from_defaults("Test Step", jobs=[])
    uj = UsageJourney("Test Journey", uj_steps=[uj_step])

    return System("Test System (No Jobs)", usage_patterns=[], servers=[server])


@pytest.fixture
def system_without_jobs_in_browser(model_builder_page: ModelBuilderPage, system_without_jobs) -> ModelBuilderPage:
    """Load a system without jobs into the browser."""
    return load_system_into_browser(model_builder_page, system_without_jobs)


# --- Cypress fixture migration helpers ---

def load_cypress_fixture(model_builder_page: ModelBuilderPage, fixture_name: str) -> ModelBuilderPage:
    """Load a Cypress JSON fixture into the browser.

    This allows reusing existing Cypress fixtures during migration.

    Args:
        model_builder_page: The page object to use
        fixture_name: Name of the fixture file (e.g., 'efootprint-model-system-data.json')

    Returns:
        The model_builder_page for chaining
    """
    fixture_path = Path(__file__).parent.parent.parent / "cypress" / "fixtures" / fixture_name
    if not fixture_path.exists():
        raise FileNotFoundError(f"Cypress fixture not found: {fixture_path}")

    model_builder_page.goto()
    model_builder_page.import_json_file(str(fixture_path))
    return model_builder_page


@pytest.fixture
def cypress_standard_model(model_builder_page: ModelBuilderPage) -> ModelBuilderPage:
    """Load the standard Cypress test model.

    This is equivalent to cy.loadEfootprintTestModel() in Cypress.
    Use this for migrating existing Cypress tests.
    """
    return load_cypress_fixture(model_builder_page, "efootprint-model-system-data.json")


@pytest.fixture
def cypress_multiple_model(model_builder_page: ModelBuilderPage) -> ModelBuilderPage:
    """Load the multiple-objects Cypress test model."""
    return load_cypress_fixture(model_builder_page, "efootprint-model-system-data-multiple.json")


@pytest.fixture
def cypress_no_job_model(model_builder_page: ModelBuilderPage) -> ModelBuilderPage:
    """Load the no-job Cypress test model."""
    return load_cypress_fixture(model_builder_page, "efootprint-model-no-job.json")
