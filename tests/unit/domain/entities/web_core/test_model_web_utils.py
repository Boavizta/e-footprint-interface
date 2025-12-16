"""Unit tests for model_web_utils helper functions."""
from datetime import datetime, timedelta

import numpy as np
import pytest
import pytz
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.constants.units import u

from model_builder.domain.entities.web_core import model_web_utils


class TestModelWebUtils:
    """Tests for time alignment and aggregation helpers."""

    def test_determine_global_time_bounds_spans_all_series(self):
        """Global window should span earliest start to latest end (inclusive)."""
        start = datetime(2025, 1, 1, tzinfo=pytz.utc)
        ehq1 = ExplainableHourlyQuantities(np.ones(24) * u.kWh, start_date=start, label="ehq1")
        ehq2 = ExplainableHourlyQuantities(np.ones(48) * u.kWh, start_date=start + timedelta(days=2), label="ehq2")

        global_start, total_hours = model_web_utils.determine_global_time_bounds([ehq1, ehq2])

        assert global_start == start.replace(hour=0, minute=0, second=0, microsecond=0)
        # From Jan 1 00:00 to Jan 4 23:00 inclusive → 3*24 up to Jan 4 00:00 non included + 24 = 96 hours
        assert total_hours == 96

    def test_reindex_array_offsets_and_zero_pads(self):
        """Reindex should offset by start date and pad with zeros."""
        start = datetime(2025, 1, 1, tzinfo=pytz.utc)
        target_start = start - timedelta(hours=2)
        ehq = ExplainableHourlyQuantities(np.array([1, 2], dtype=np.float32) * u.kWh, start_date=start, label="ehq")

        padded = model_web_utils.reindex_array(ehq, target_start, total_hours=5)

        np.testing.assert_array_equal(padded.magnitude, np.array([0, 0, 1, 2, 0], dtype=np.float32))
        assert padded.units == u.kWh

    def test_get_reindexed_array_from_dict(self):
        """Should yield values in tonne with correct length."""
        start = datetime(2025, 1, 1, tzinfo=pytz.utc)
        ehq = ExplainableHourlyQuantities(np.array([1, 1, 1], dtype=np.float32) * u.kg, start_date=start, label="ehq")
        global_start = start - timedelta(hours=1)
        reindexed_present = model_web_utils.get_reindexed_array_from_dict(
            "present", {"present": ehq}, global_start, total_hours=4)

        # kg converted to tonnes
        np.testing.assert_array_equal(reindexed_present.magnitude, np.array([0, 0.001, 0.001, 0.001], dtype=np.float32))
        assert reindexed_present.units == u.tonne

    @pytest.mark.parametrize(
        "unit,values,expected",
        [
            (u.kWh, np.array([1, 3] * 24, dtype=np.float32), [48.0, 48.0]), # Daily aggregate by sum
            (u.cpu_core, np.array([1, 3] * 24, dtype=np.float32), [2.0, 2.0]), # Daily aggregate by mean
        ],
    )
    def test_to_rounded_daily_values_respects_aggregation_strategy(self, unit, values, expected):
        """Sum for cumulative units, mean for resource allocation units."""
        arr = values * unit

        result = model_web_utils.to_rounded_daily_values(arr, rounding_depth=1)

        assert result == expected
