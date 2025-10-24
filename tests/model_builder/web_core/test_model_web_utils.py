import numpy as np
import pytz
from datetime import datetime
from efootprint.constants.units import u
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities

from model_builder.web_core.model_web_utils import (
    to_rounded_daily_values,
    determine_global_time_bounds,
    reindex_array,
)


class TestToRoundedDailyValues:
    """Test suite for the to_rounded_daily_values function."""

    def test_sum_aggregation_energy_full_days(self):
        """Test sum aggregation with energy units over complete days."""
        # 2 days: day 1 has all 1 kWh/hour, day 2 has all 2 kWh/hour
        hourly_values = np.array([1.0] * 24 + [2.0] * 24, dtype=np.float32) * u.kWh

        result = to_rounded_daily_values(hourly_values)

        assert result == [24.0, 48.0]

    def test_sum_aggregation_partial_day(self):
        """Test sum aggregation with incomplete last day."""
        # 1 full day + 12 hours of carbon footprint
        hourly_values = np.array([1.0] * 24 + [2.0] * 12, dtype=np.float32) * u.kg

        result = to_rounded_daily_values(hourly_values)

        assert result == [24.0, 24.0]  # 12 hours × 2 kg = 24 kg

    def test_mean_aggregation_cpu_cores_full_days(self):
        """Test mean aggregation with CPU cores over complete days."""
        # Day 1: ramp from 0 to 23 cores, Day 2: constant 10 cores
        hourly_values = np.array(list(range(24)) + [10.0] * 24, dtype=np.float32) * u.cpu_core

        result = to_rounded_daily_values(hourly_values)

        # Day 1 mean: (0+1+2+...+23)/24 = 11.5 cores
        # Day 2 mean: 10.0 cores
        assert result == [11.5, 10.0]

    def test_mean_aggregation_ram_partial_day(self):
        """Test mean aggregation with RAM over incomplete last day."""
        # 1 full day of 5 GB + 6 hours of 10 GB
        hourly_values = np.array([5.0] * 24 + [10.0] * 6, dtype=np.float32) * u.GB_ram

        result = to_rounded_daily_values(hourly_values)

        assert result == [5.0, 10.0]  # Mean of partial day is 10.0 GB

    def test_mean_aggregation_single_hour(self):
        """Test mean aggregation with a single hour."""
        hourly_values = np.array([42.0], dtype=np.float32) * u.cpu_core

        result = to_rounded_daily_values(hourly_values)

        assert result == [42.0]

    def test_custom_rounding_depth(self):
        """Test custom rounding depth parameter."""
        hourly_values = np.array([1.123456789] * 24, dtype=np.float32) * u.kWh

        result = to_rounded_daily_values(hourly_values, rounding_depth=2)

        # Sum: 1.123456789 * 24 ≈ 26.96, rounded to 2 decimals
        assert result == [26.96]


class TestDetermineGlobalTimeBounds:
    """Test suite for the determine_global_time_bounds function."""

    def test_single_ehq_starting_at_midnight(self):
        """Test with a single ExplainableHourlyQuantities starting at midnight UTC."""
        start_date = datetime(2024, 1, 1, 0, 0, tzinfo=pytz.utc)
        values = np.array([1.0] * 48, dtype=np.float32) * u.kWh
        ehq = ExplainableHourlyQuantities(values, start_date=start_date, label="test")

        global_start, total_hours = determine_global_time_bounds([ehq])

        assert global_start == start_date
        assert total_hours == 48

    def test_multiple_ehqs_same_start(self):
        """Test with multiple EHQs starting at the same time."""
        start_date = datetime(2024, 1, 1, 0, 0, tzinfo=pytz.utc)
        values1 = np.array([1.0] * 24, dtype=np.float32) * u.kWh
        values2 = np.array([2.0] * 48, dtype=np.float32) * u.kg
        ehq1 = ExplainableHourlyQuantities(values1, start_date=start_date, label="ehq1")
        ehq2 = ExplainableHourlyQuantities(values2, start_date=start_date, label="ehq2")

        global_start, total_hours = determine_global_time_bounds([ehq1, ehq2])

        assert global_start == start_date
        assert total_hours == 48  # Longest duration

    def test_multiple_ehqs_different_starts(self):
        """Test with EHQs starting at different times."""
        start1 = datetime(2024, 1, 1, 0, 0, tzinfo=pytz.utc)
        start2 = datetime(2024, 1, 2, 0, 0, tzinfo=pytz.utc)  # 1 day later
        values1 = np.array([1.0] * 24, dtype=np.float32) * u.kWh
        values2 = np.array([2.0] * 24, dtype=np.float32) * u.kg
        ehq1 = ExplainableHourlyQuantities(values1, start_date=start1, label="ehq1")
        ehq2 = ExplainableHourlyQuantities(values2, start_date=start2, label="ehq2")

        global_start, total_hours = determine_global_time_bounds([ehq1, ehq2])

        assert global_start == start1  # Earliest start
        assert total_hours == 48  # From start1 (day 1) to end of ehq2 (day 3)

    def test_ehq_starting_not_at_midnight(self):
        """Test with EHQ not starting at midnight (should still align to midnight)."""
        start_date = datetime(2024, 1, 1, 6, 30, tzinfo=pytz.utc)  # 6:30 AM
        values = np.array([1.0] * 24, dtype=np.float32) * u.kWh
        ehq = ExplainableHourlyQuantities(values, start_date=start_date, label="test")

        global_start, total_hours = determine_global_time_bounds([ehq])

        # Should align to midnight of the same day
        assert global_start == datetime(2024, 1, 1, 0, 0, tzinfo=pytz.utc)
        assert total_hours == 30  # From midnight (hour 0) through 6:30 AM + 24 hours (to hour 29)


class TestReindexArray:
    """Test suite for the reindex_array function."""

    def test_reindex_starting_at_global_start(self):
        """Test reindexing when EHQ starts at global_start."""
        start_date = datetime(2024, 1, 1, 0, 0, tzinfo=pytz.utc)
        values = np.array([1.0, 2.0, 3.0], dtype=np.float32) * u.kWh
        ehq = ExplainableHourlyQuantities(values, start_date=start_date, label="test")

        result = reindex_array(ehq, global_start=start_date, total_hours=5)

        expected = np.array([1.0, 2.0, 3.0, 0.0, 0.0], dtype=np.float32) * u.kWh
        np.testing.assert_array_equal(result.magnitude, expected.magnitude)
        assert result.units == expected.units

    def test_reindex_with_offset(self):
        """Test reindexing when EHQ starts after global_start."""
        global_start = datetime(2024, 1, 1, 0, 0, tzinfo=pytz.utc)
        ehq_start = datetime(2024, 1, 1, 2, 0, tzinfo=pytz.utc)  # 2 hours later
        values = np.array([10.0, 20.0], dtype=np.float32) * u.kg
        ehq = ExplainableHourlyQuantities(values, start_date=ehq_start, label="test")

        result = reindex_array(ehq, global_start=global_start, total_hours=6)

        expected = np.array([0.0, 0.0, 10.0, 20.0, 0.0, 0.0], dtype=np.float32) * u.kg
        np.testing.assert_array_equal(result.magnitude, expected.magnitude)
        assert result.units == expected.units

    def test_reindex_exact_fit(self):
        """Test reindexing when EHQ exactly fills the reindexed array."""
        start_date = datetime(2024, 1, 1, 0, 0, tzinfo=pytz.utc)
        values = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32) * u.kWh
        ehq = ExplainableHourlyQuantities(values, start_date=start_date, label="test")

        result = reindex_array(ehq, global_start=start_date, total_hours=4)

        expected = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32) * u.kWh
        np.testing.assert_array_equal(result.magnitude, expected.magnitude)

    def test_reindex_preserves_units(self):
        """Test that reindexing preserves the original units."""
        start_date = datetime(2024, 1, 1, 0, 0, tzinfo=pytz.utc)
        values = np.array([5.0], dtype=np.float32) * u.cpu_core
        ehq = ExplainableHourlyQuantities(values, start_date=start_date, label="test")

        result = reindex_array(ehq, global_start=start_date, total_hours=3)

        assert result.units == u.cpu_core
        np.testing.assert_array_equal(result.magnitude, np.array([5.0, 0.0, 0.0], dtype=np.float32))
