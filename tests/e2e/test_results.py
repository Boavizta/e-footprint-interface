"""Tests for the results panel and emissions display."""
import pytest
from playwright.sync_api import expect

from efootprint.api_utils.system_to_json import system_to_json

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage
from tests.fixtures import build_minimal_system


@pytest.fixture
def system_dict_complete():
    """Create a complete system dict that can calculate results."""
    system = build_minimal_system("Test System")
    return system_to_json(system, save_calculated_attributes=True)


@pytest.fixture
def complete_system_in_browser(model_builder_page: ModelBuilderPage, system_dict_complete):
    """Load complete system into browser."""
    return load_system_dict_into_browser(model_builder_page, system_dict_complete)


@pytest.mark.e2e
class TestResultsPanel:
    """Tests for the results panel functionality."""

    def test_open_and_close_result_panel(self, complete_system_in_browser: ModelBuilderPage):
        """Test opening and closing the result panel.

        Uses complete system fixture which has a complete model ready for calculation.
        """
        model_builder = complete_system_in_browser
        page = model_builder.page

        # Open result panel
        model_builder.open_result_panel()
        model_builder.result_chart_should_be_visible()
        expect(page.locator("#graph-block")).to_be_visible()
        expect(page.locator("#result-block")).to_be_visible()

        # Close result panel
        model_builder.close_result_panel()
        expect(page.locator("#lineChart")).not_to_be_visible()
