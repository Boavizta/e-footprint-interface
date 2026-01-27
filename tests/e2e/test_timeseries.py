"""Tests for timeseries generation and validation in usage patterns.

These tests verify:
1. Chart persistence when opening/reopening forms
2. Modeling duration validation (min/max based on unit)
3. Error message display and clearing
4. Responsive behavior on mobile/tablet devices
"""
import pytest
from playwright.sync_api import expect

from tests.e2e.pages import ModelBuilderPage


@pytest.mark.e2e
class TestTimeseriesChartDisplay:
    """Tests for timeseries chart rendering and persistence."""

    def test_chart_persists_across_multiple_form_opens(self, empty_model_builder: ModelBuilderPage):
        """Chart should render consistently when opening usage pattern forms multiple times.

        This test verifies that:
        - Chart canvas exists when creating first UP
        - Chart renders with different inputs for second UP
        - Chart re-renders when editing existing UP
        """
        model_builder = empty_model_builder
        page = model_builder.page

        uj_name = "Test E2E UJ"
        up_name_one = "Test E2E Usage Pattern 1"
        up_name_two = "Test E2E Usage Pattern 2"

        # Create usage journey
        model_builder.click_add_usage_journey()
        page.locator("#UsageJourney_name").fill(uj_name)
        model_builder.side_panel.submit_and_wait_for_close()

        # Verify UJ created with leader line
        uj_card = model_builder.get_object_card("UsageJourney", uj_name)
        uj_card.should_have_class("leader-line-object")

        # Create first usage pattern
        model_builder.click_add_usage_pattern()
        model_builder.side_panel.should_be_visible()

        # Chart should be hidden initially
        expect(page.locator("#chartTimeseries")).to_contain_class("d-none")

        # Verify canvas element exists
        expect(page.locator("#timeSeriesChart")).to_be_attached()

        # Fill in timeseries form fields
        page.locator("#UsagePattern_name").fill(up_name_one)
        page.locator("#UsagePattern_hourly_usage_journey_starts__modeling_duration_value").click()
        page.locator("#UsagePattern_hourly_usage_journey_starts__modeling_duration_value").fill("2")
        page.locator("#UsagePattern_hourly_usage_journey_starts__net_growth_rate_in_percentage").click()
        page.locator("#UsagePattern_hourly_usage_journey_starts__net_growth_rate_in_percentage").fill("25")
        page.locator("#UsagePattern_hourly_usage_journey_starts__net_growth_rate_timespan").select_option("year")
        page.locator("#UsagePattern_hourly_usage_journey_starts__initial_volume").fill("1000")

        # Submit first UP
        model_builder.side_panel.submit_and_wait_for_close()

        # Create second usage pattern with different values
        model_builder.click_add_usage_pattern()
        model_builder.side_panel.should_be_visible()
        page.locator("#UsagePattern_name").fill(up_name_two)
        page.locator("#UsagePattern_hourly_usage_journey_starts__modeling_duration_value").click()
        page.locator("#UsagePattern_hourly_usage_journey_starts__modeling_duration_value").fill("5")
        page.locator("#UsagePattern_hourly_usage_journey_starts__net_growth_rate_in_percentage").click()
        page.locator("#UsagePattern_hourly_usage_journey_starts__net_growth_rate_in_percentage").fill("15")
        page.locator("#UsagePattern_hourly_usage_journey_starts__net_growth_rate_timespan").select_option("month")
        page.locator("#UsagePattern_hourly_usage_journey_starts__initial_volume").fill("1000")

        # Verify canvas still exists and is attached
        expect(page.locator("#timeSeriesChart")).to_be_attached()

        # Submit second UP
        model_builder.side_panel.submit_and_wait_for_close()

        # Re-open first UP to verify chart renders again
        up_card = model_builder.get_object_card("UsagePattern", up_name_one)
        up_card.click_edit_button()

        # Chart should be visible now (d-block)
        expect(page.locator("#chartTimeseries")).to_contain_class("d-block")

        # Verify canvas exists and is attached
        expect(page.locator("#timeSeriesChart")).to_be_attached()


@pytest.mark.e2e
class TestTimeseriesValidation:
    """Tests for modeling duration validation with different units."""

    def test_modeling_duration_validation_with_day_and_month_units(self, empty_model_builder: ModelBuilderPage):
        """Modeling duration should validate against max values that change based on unit.

        This test verifies:
        - Valid values don't show error messages
        - Values exceeding max show error message with max value
        - Value of 0 shows error message and is corrected to min value
        - Max value changes when switching from day to month unit
        """
        model_builder = empty_model_builder
        page = model_builder.page

        # Create usage pattern
        model_builder.click_add_usage_pattern()

        # Test valid value (2 days) - no error
        duration_field = page.locator("#UsagePattern_hourly_usage_journey_starts__modeling_duration_value")
        duration_field.click()
        duration_field.fill("2")
        duration_field.dispatch_event("input")
        expect(page.locator("#modeling_duration_value_error_message")).not_to_be_visible()

        # Test value exceeding max (15 years - should exceed max for year unit)
        duration_field.fill("15")
        # Get max value and verify it's exceeded
        max_value = duration_field.get_attribute("max")
        current_value = int(duration_field.input_value())
        assert current_value <= int(max_value), f"Value {current_value} should be <= max {max_value}"
        # Error message should display the max value
        error_message = page.locator("#modeling_duration_value_error_message")
        expect(error_message).to_contain_text(f"Modeling duration value must be less than or equal to {max_value}")

        # Test value of 0 - should be corrected to 1 and show error
        duration_field.fill("0")
        # Value should be corrected to 1 (min value)
        current_value = int(duration_field.input_value())
        assert current_value == 1, "Value should be corrected to 1"
        # Error message should indicate min value
        expect(error_message).to_contain_text("Modeling duration value must be greater than 0 and can't be empty")

        # Switch to month unit
        page.locator("#UsagePattern_hourly_usage_journey_starts__modeling_duration_unit").select_option("month")
        # Test valid value for month (12 months) - no error
        duration_field.fill("12")
        expect(error_message).not_to_be_visible()

        # Test value exceeding max for month unit (150 months)
        duration_field.fill("150")
        # Get new max value for month unit and verify
        max_value = duration_field.get_attribute("max")
        current_value = int(duration_field.input_value())
        assert current_value <= int(max_value), f"Value {current_value} should be <= max {max_value}"
        # Error message should display
        expect(error_message).to_contain_text(f"Modeling duration value must be less than or equal to {max_value}")

        # Test value of 0 with month unit - should be corrected to 12
        duration_field.fill("0")
        # Value should be corrected to 12 (min value for month)
        current_value = int(duration_field.input_value())
        assert current_value == 12, "Value should be corrected to 12 for month unit"

        expect(error_message).to_contain_text("Modeling duration value must be greater than 0 and can't be empty")

        # Clear error by setting valid value
        duration_field.fill("24")
        expect(error_message).not_to_be_visible()

    def test_edit_usage_pattern_with_month_unit_validation(self, empty_model_builder: ModelBuilderPage):
        """When editing UP created with month unit, max validation should work correctly.

        This verifies that the max value constraint is properly set when reopening
        a form for an existing object with a specific duration unit.
        """
        model_builder = empty_model_builder
        page = model_builder.page

        up_name = "Test E2E Usage Pattern 1"

        # Create usage pattern with month unit
        model_builder.click_add_usage_pattern()
        model_builder.side_panel.should_be_visible()
        page.locator("#UsagePattern_name").fill(up_name)
        duration_unit_locator = page.locator("#UsagePattern_hourly_usage_journey_starts__modeling_duration_unit")
        duration_unit_locator.click()
        duration_unit_locator.select_option("month")
        duration_unit_locator.click() # Need to encapsulate selection between clicks to trigger hyperscript logic.

        # Set a valid value (15 months)
        duration_field = page.locator("#UsagePattern_hourly_usage_journey_starts__modeling_duration_value")
        duration_field.fill("15")
        # Should not show error for 15 months
        expect(page.locator("#modeling_duration_value_error_message")).not_to_be_visible()

        # Fill initial volume and submit
        page.locator("#UsagePattern_hourly_usage_journey_starts__initial_volume").fill("1000")
        model_builder.side_panel.submit_and_wait_for_close()

        # Re-open the usage pattern for editing
        up_card = model_builder.get_object_card("UsagePattern", up_name)
        up_card.click_edit_button()

        # Try to set a higher value (25 months)
        duration_field.fill("25")
        # Should NOT show error about max value being 10
        expect(page.locator("#modeling_duration_value_error_message")).not_to_be_visible()

        # Try selecting back year unit ==> max should be 10 and error should be shown
        duration_unit_locator.click()
        duration_unit_locator.select_option("year")
        duration_unit_locator.click()
        expect(page.locator("#modeling_duration_value_error_message")).to_contain_text(
            "Modeling duration value must be less than or equal to 10")
        current_value = int(duration_field.input_value())
        assert current_value == 10, f"Value should be corrected to 10 for year unit, but is {current_value}"


@pytest.mark.e2e
class TestTimeseriesResponsiveChart:
    """Tests for timeseries chart responsive behavior on mobile/tablet."""

    def test_chart_hidden_on_iphone_viewport(self, model_builder_page: ModelBuilderPage):
        """On iPhone viewport, chart should exist but remain empty (hidden).

        This tests responsive behavior where the chart is hidden on small screens
        to save space and improve UX.
        """
        model_builder = model_builder_page
        page = model_builder.page

        # Set iPhone X viewport
        page.set_viewport_size({"width": 375, "height": 812})

        # Navigate to model builder
        model_builder.goto()

        # Open usage pattern form
        page.locator("button").filter(has_text="Add usage pattern").click()
        page.locator("#UsagePattern_hourly_usage_journey_starts__initial_volume").fill("1000")

        # Chart canvas should exist but be empty (not rendered on mobile)
        chart_canvas = page.locator("#timeSeriesChart")
        expect(chart_canvas).to_be_attached()

        # On mobile, chart should not be visible/rendered
        # We verify this by checking the chartTimeseries container is hidden
        expect(page.locator("#chartTimeseries")).to_contain_class("d-none")

    def test_chart_hidden_on_ipad_viewport(self, model_builder_page: ModelBuilderPage):
        """On iPad viewport, chart should exist but remain empty (hidden).

        Similar to iPhone test but for tablet viewport size.
        """
        model_builder = model_builder_page
        page = model_builder.page

        # Set iPad Mini viewport
        page.set_viewport_size({"width": 768, "height": 1024})

        # Navigate to model builder
        model_builder.goto()

        # Open usage pattern form
        page.locator("button").filter(has_text="Add usage pattern").click()
        page.locator("#UsagePattern_hourly_usage_journey_starts__initial_volume").fill("1000")

        # Chart canvas should exist but be empty (not rendered on tablet)
        chart_canvas = page.locator("#timeSeriesChart")
        expect(chart_canvas).to_be_attached()

        # On tablet, chart should not be visible/rendered
        expect(page.locator("#chartTimeseries")).to_contain_class("d-none")
