"""Unit tests for explainable_timeseries_utils helpers."""
from datetime import datetime

import numpy as np
import pytz
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.constants.units import u

from model_builder.domain.entities.web_core.explainable_timeseries_utils import (
    prepare_hourly_quantity_data,
    prepare_recurrent_quantity_data,
    prepare_timeseries_chart_context,
)
from tests.unit.domain.entities.web_core.helpers import DummyExplainableWeb, DummyModelWeb, DummyWebObj


class TestExplainableTimeseriesUtils:
    """Tests for timeseries chart context helpers."""

    def test_prepare_hourly_quantity_data_midnight_start(self):
        """Aggregates hourly quantities per day when start is at midnight."""
        start = datetime(2025, 1, 1, tzinfo=pytz.utc)
        values = np.array([1] * 24 + [2] * 24, dtype=np.float32) * u.kWh
        ehq = ExplainableHourlyQuantities(values, start_date=start, label="ehq")

        data, extra = prepare_hourly_quantity_data(DummyExplainableWeb(ehq))

        assert data == {"2025-01-01": 24.0, "2025-01-02": 48.0}
        assert extra["aggregation_strategy"] == "sum"

    def test_prepare_hourly_quantity_data_non_midnight_reindexes(self):
        """Pads and reindexes when start hour is non-zero."""
        start = datetime(2025, 1, 1, 6, tzinfo=pytz.utc)
        values = np.array([1, 2, 3, 4], dtype=np.float32) * u.kWh
        ehq = ExplainableHourlyQuantities(values, start_date=start, label="ehq")

        data, _ = prepare_hourly_quantity_data(DummyExplainableWeb(ehq))

        # 6 hours padded with zeros before the 4 values → total sum 10 for the day
        assert data == {"2025-01-01": 10.0}

    def test_prepare_recurrent_quantity_data(self):
        """Returns hour-indexed dict of recurrent magnitudes."""
        recurrent = ExplainableHourlyQuantities(
            np.array([1.5, 2.5, 3.5], dtype=np.float32) * u.kWh,
            start_date=datetime(2025, 1, 1, tzinfo=pytz.utc), label="recurrent")
        data, extra = prepare_recurrent_quantity_data(DummyExplainableWeb(recurrent))

        assert data == {"0": 1.5, "1": 2.5, "2": 3.5}
        assert extra == {}

    def test_prepare_timeseries_chart_context_passes_literal_and_data(self):
        """prepare_timeseries_chart_context wires web_explainable and data together."""
        start = datetime(2025, 1, 1, tzinfo=pytz.utc)
        values = np.array([1, 1, 1, 1], dtype=np.float32) * u.kWh
        ehq = ExplainableHourlyQuantities(values, start_date=start, label="ehq")
        web_explainable = DummyExplainableWeb(ehq)
        web_obj = DummyWebObj("usage", web_explainable)
        model_web = DummyModelWeb(web_obj)

        context, returned_explainable = prepare_timeseries_chart_context(
            model_web, efootprint_id="obj1", attr_name="usage", data_preparer_func=prepare_hourly_quantity_data)

        assert returned_explainable is web_explainable
        assert context["web_explainable"] is web_explainable
        assert context["literal_formula"] == "x"
        assert context["data_timeseries"]["2025-01-01"] == 4.0
