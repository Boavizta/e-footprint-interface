"""Unit tests for explainable_timeseries_utils helpers."""

from datetime import datetime
from types import SimpleNamespace

import numpy as np
import pytz
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.constants.units import u

from model_builder.domain.entities.web_core.explainable_timeseries_utils import (
    get_web_explainable_from_attr,
    prepare_hourly_quantity_data,
    prepare_hourly_quantity_period_data,
    prepare_recurrent_quantity_data,
    prepare_timeseries_chart_context,
    weekly_hour_labels,
)
from tests.unit_tests.domain.entities.web_core.helpers import DummyExplainableWeb, DummyModelWeb, DummyWebObj


class TestExplainableTimeseriesUtils:
    """Tests for timeseries chart context helpers."""

    def test_prepare_hourly_quantity_data_midnight_start(self):
        """Aggregates hourly quantities per day when start is at midnight."""
        start = datetime(2025, 1, 1, tzinfo=pytz.utc)
        values = np.array([1] * 24 + [2] * 24, dtype=np.float32) * u.kWh
        ehq = ExplainableHourlyQuantities(values, start_date=start, label="ehq")

        data, extra = prepare_hourly_quantity_data(ehq)

        assert data == {"2025-01-01": 24.0, "2025-01-02": 48.0}
        assert extra["aggregation_strategy"] == "sum"

    def test_prepare_hourly_quantity_data_non_midnight_reindexes(self):
        """Pads and reindexes when start hour is non-zero."""
        start = datetime(2025, 1, 1, 6, tzinfo=pytz.utc)
        values = np.array([1, 2, 3, 4], dtype=np.float32) * u.kWh
        ehq = ExplainableHourlyQuantities(values, start_date=start, label="ehq")

        data, _ = prepare_hourly_quantity_data(ehq)

        # 6 hours padded with zeros before the 4 values → total sum 10 for the day
        assert data == {"2025-01-01": 10.0}

    def test_prepare_hourly_quantity_period_data_uses_calendar_boundaries(self):
        start = datetime(2024, 12, 31, tzinfo=pytz.utc)
        values = np.concatenate((np.full(24, 2, dtype=np.float32), np.full(24, 3, dtype=np.float32))) * u.occurrence
        ehq = ExplainableHourlyQuantities(values, start_date=start, label="ehq")

        data = prepare_hourly_quantity_period_data(ehq)

        assert data == {
            "month": {"2024-12": 48.0, "2025-01": 72.0},
            "year": {"2024": 48.0, "2025": 72.0},
        }

    def test_prepare_hourly_quantity_period_data_keeps_raw_magnitudes_above_display_prefix_threshold(self):
        start = datetime(2025, 1, 1, tzinfo=pytz.utc)
        values = np.full(48, 1_000_000, dtype=np.float32) * u.occurrence
        ehq = ExplainableHourlyQuantities(values, start_date=start, label="ehq")

        data = prepare_hourly_quantity_period_data(ehq)

        assert data == {
            "month": {"2025-01": 48_000_000.0},
            "year": {"2025": 48_000_000.0},
        }

    def test_prepare_recurrent_quantity_data(self):
        """Returns hour-indexed dict of recurrent magnitudes."""
        recurrent = ExplainableRecurrentQuantities(
            np.array([1.5, 2.5, 3.5], dtype=np.float32) * u.kWh, label="recurrent"
        )
        data, extra = prepare_recurrent_quantity_data(recurrent)

        assert data == {"0": 1.5, "1": 2.5, "2": 3.5}
        assert extra == {"display_unit": "kWh"}

    def test_prepare_recurrent_quantity_data_accepts_canonical_week_labels(self):
        recurrent = ExplainableRecurrentQuantities(np.arange(168, dtype=np.float32) * u.kWh, label="recurrent")

        data, _ = prepare_recurrent_quantity_data(recurrent, weekly_hour_labels())

        assert len(data) == 168
        assert data["Mon 00:00"] == 0
        assert data["Sun 23:00"] == 167

    def test_prepare_timeseries_chart_context_passes_literal_and_data(self):
        """prepare_timeseries_chart_context wires web_explainable and data together."""
        start = datetime(2025, 1, 1, tzinfo=pytz.utc)
        values = np.array([1, 1, 1, 1], dtype=np.float32) * u.kWh
        ehq = ExplainableHourlyQuantities(values, start_date=start, label="ehq")
        web_explainable = DummyExplainableWeb(ehq)
        web_obj = DummyWebObj("usage", web_explainable)
        model_web = DummyModelWeb(web_obj)

        context, returned_explainable = prepare_timeseries_chart_context(
            model_web, efootprint_id="obj1", attr_name="usage", data_preparer_func=prepare_hourly_quantity_data
        )

        assert returned_explainable is web_explainable
        assert context["web_explainable"] is web_explainable
        assert context["literal_formula"] == "x"
        assert context["data_timeseries"]["2025-01-01"] == 4.0

    def test_saved_recurrent_chart_context_uses_raw_timeseries_helper(self):
        recurrent = ExplainableRecurrentQuantities(
            np.arange(168, dtype=np.float32) * u.cpu_core, label="saved recurrent"
        )
        web_explainable = SimpleNamespace(
            efootprint_object=recurrent,
            compute_literal_formula_and_ancestors_mapped_to_symbols_list=lambda: ("saved formula", ["source"]),
        )
        model_web = DummyModelWeb(DummyWebObj("recurrent_need", web_explainable))

        context, returned_explainable = prepare_timeseries_chart_context(
            model_web,
            efootprint_id="need-1",
            attr_name="recurrent_need",
            data_preparer_func=prepare_recurrent_quantity_data,
        )

        assert returned_explainable is web_explainable
        assert context["data_timeseries"] == {str(hour): float(hour) for hour in range(168)}
        assert context["display_unit"] == "cpu core"
        assert context["literal_formula"] == "saved formula"
        assert context["ancestors_mapped_to_symbols_list"] == ["source"]

    def test_get_web_explainable_from_attr_wraps_quantity_inside_dict(self):
        scalar = ExplainableQuantity(1 * u.dimensionless, label="scalar")
        dict_wrapper = SimpleNamespace(efootprint_object={"system-id": scalar})
        model_web = DummyModelWeb(DummyWebObj("impact_repartition_weights", dict_wrapper))

        resolved = get_web_explainable_from_attr(
            model_web,
            efootprint_id="obj1",
            attr_name="impact_repartition_weights",
            id_of_key_in_dict="system-id",
        )

        assert resolved.efootprint_object is scalar
        assert resolved.rounded_value == 1

    def test_get_web_explainable_from_attr_resolves_escaped_coordinate_id(self):
        class Coordinate:
            id = "pattern/step"

            def __str__(self):
                return "Pattern / Step"

        coordinate = Coordinate()
        scalar = ExplainableQuantity(1 * u.dimensionless, label="scalar")
        dict_wrapper = SimpleNamespace(efootprint_object={coordinate: scalar})
        model_web = DummyModelWeb(DummyWebObj("hourly_values", dict_wrapper))

        resolved = get_web_explainable_from_attr(
            model_web,
            efootprint_id="obj1",
            attr_name="hourly_values",
            id_of_key_in_dict="pattern2fstep",
        )

        assert resolved.efootprint_object is scalar
