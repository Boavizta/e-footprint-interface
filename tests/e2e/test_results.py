"""Tests for the results panel and emissions display."""
import re
from datetime import datetime

import pytest
from playwright.sync_api import expect

from tests.e2e.pages import ModelBuilderPage


@pytest.mark.e2e
class TestResultsPanel:
    """Tests for the results panel functionality."""

    def test_open_and_close_result_panel(self, minimal_complete_model_builder: ModelBuilderPage):
        """Test opening and closing the result panel.

        Uses complete system fixture which has a complete model ready for calculation.
        """
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Open result panel
        model_builder.open_result_panel()
        model_builder.result_chart_should_be_visible()
        expect(page.locator("#graph-block")).to_be_visible()
        expect(page.locator("#result-block")).to_be_visible()

        # Close result panel
        model_builder.close_result_panel()
        expect(page.locator("#lineChart")).not_to_be_visible()

    def test_error_modal_when_model_incomplete(self, empty_model_builder: ModelBuilderPage):
        """Error modal should appear when trying to calculate incomplete model."""
        model_builder = empty_model_builder
        page = model_builder.page

        # Try to open result panel on empty/incomplete model
        page.locator("#btn-open-panel-result").click()

        # Error modal should appear with "Go back" button
        go_back_button = page.locator("button").filter(has_text="Go back")
        expect(go_back_button).to_be_attached()

        # Result panel should NOT be visible
        expect(page.locator("#lineChart")).not_to_be_visible()

    def test_granularity_change_updates_chart_labels(self, minimal_complete_model_builder: ModelBuilderPage):
        """Changing temporal granularity should update chart label count."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Open result panel
        model_builder.open_result_panel()
        bar_chart_exists = page.evaluate("window.charts.barChart")
        assert len(bar_chart_exists) > 10, "window.charts.barChart should exist"

        # Get initial label count (default is yearly)
        initial_label_count = page.evaluate("window.charts.barChart.data.labels.length")

        # Change to monthly granularity
        page.locator("#results_temporal_granularity").select_option("month")
        expect(page.locator("#results_temporal_granularity")).to_have_value("month")

        # Wait for chart to update
        page.wait_for_timeout(100)

        # Get monthly label count (should be more than yearly)
        monthly_label_count = page.evaluate("window.charts.barChart.data.labels.length")
        assert monthly_label_count > initial_label_count, \
            f"Monthly labels ({monthly_label_count}) should be more than yearly ({initial_label_count})"

        # Change to yearly granularity
        page.locator("#results_temporal_granularity").select_option("year")

        # Wait for chart to update
        page.wait_for_timeout(100)

        # Get yearly label count (should match initial)
        yearly_label_count = page.evaluate("window.charts.barChart.data.labels.length")
        assert yearly_label_count == initial_label_count, \
            f"Yearly labels ({yearly_label_count}) should match initial ({initial_label_count})"

    def test_sources_tab_display_and_export(self, minimal_complete_model_builder: ModelBuilderPage):
        """Sources tab should toggle view and allow download with correct filename."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Open result panel
        model_builder.open_result_panel()

        # Click Sources button
        page.locator("#header-btn-result-sources").click()

        # Verify source-block is visible and graph-block is hidden
        expect(page.locator("#source-block")).to_have_class(re.compile(r"d-block"))
        expect(page.locator("#graph-block")).to_have_class(re.compile(r"d-none"))

        # Test sources download
        with page.expect_download() as download_info:
            page.locator("#download-sources").click()

        download = download_info.value
        filename = download.suggested_filename

        # Verify filename format: YYYY-MM-DD HH:MM_UTC system name_sources.xlsx
        current_date = datetime.now().strftime("%Y-%m-%d")
        assert current_date in filename
        assert "UTC" in filename
        assert "Test System" in filename
        assert filename.endswith("_sources.xlsx")

        # Toggle back to graph view
        page.locator("#header-btn-result-chart").click()
        expect(page.locator("#graph-block")).to_have_class(re.compile(r"d-block"))
        expect(page.locator("#source-block")).to_have_class(re.compile(r"d-none"))

    def test_model_recomputation_with_result_panel_open(self, minimal_complete_model_builder: ModelBuilderPage):
        """Chart should update when editing object with result panel open."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Open server for editing
        server_card = model_builder.get_object_card("Server", "Test Server")
        server_card.click_edit_button()

        # Modify storage replication factor
        page.locator("#Storage_data_replication_factor").fill("1000")

        # Open result panel (side panel should stay open)
        model_builder.open_result_panel()

        # Verify chart title
        expect(page.locator("#barChartTitle")).to_contain_text("Yearly CO2 emissions")

        # Verify panel has result-width class (indicating side panel is open)
        expect(page.locator("#panel-result-btn")).to_have_class(re.compile(r"result-width"))

        # Store initial chart data
        initial_chart_data = page.evaluate("JSON.stringify(window.charts.barChart.data)")

        # Submit form (edit server)
        model_builder.side_panel.submit_and_wait_for_close()

        # Wait for chart to update
        page.wait_for_timeout(100)

        # Verify chart was redrawn with different data
        new_chart_data = page.evaluate("JSON.stringify(window.charts.barChart.data)")
        assert new_chart_data != initial_chart_data, "Chart data should have changed after edit"

        # Verify panel no longer has result-width class (side panel closed)
        expect(page.locator("#panel-result-btn")).not_to_have_class(re.compile(r"result-width"))
