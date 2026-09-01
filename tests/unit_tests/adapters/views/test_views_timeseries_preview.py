"""Tests for stateless recurrent-timeseries draft previews."""

import html
import json
import re
from copy import deepcopy

import numpy as np
import pytest
from django.test import RequestFactory
from efootprint.builders.timeseries import (
    ExplainableHourlyQuantitiesFromFormInputs,
    ExplainableRecurrentQuantitiesFromWeeklyPattern,
)

from model_builder.adapters.views.views_timeseries_preview import timeseries_preview


OBJECT_TYPE = "RecurrentEdgeProcess"
FIELD_NAME = "recurrent_compute_needed"


def weekly_inputs(baseline=2, range_value=5):
    return {
        "unit": "cpu_core",
        "profiles": [
            {
                "name": "weekday",
                "days": [0, 1, 2, 3, 4],
                "baseline": baseline,
                "ranges": [{"start": 8, "end": 18, "value": range_value}],
            },
            {"name": "weekend", "days": [5, 6], "baseline": 1, "ranges": []},
        ],
    }


def preview_request(form_inputs, **overrides):
    data = {
        "object_type": OBJECT_TYPE,
        "field_name": FIELD_NAME,
        "builder": "weekly_pattern",
        "form_inputs": json.dumps(form_inputs),
        "preview_id": "compute-preview",
        "request_sequence": "4",
        **overrides,
    }
    request = RequestFactory().post("/model_builder/timeseries-preview/", data)
    request.session = {"sentinel": {"unchanged": True}}
    return request


def hourly_inputs(duration_value=2, duration_unit="year"):
    return {
        "start_date": "2025-01-01",
        "modeling_duration_value": duration_value,
        "modeling_duration_unit": duration_unit,
        "initial_volume": 3000,
        "initial_volume_timespan": "month",
        "net_growth_rate_in_percentage": 12,
        "net_growth_rate_timespan": "year",
    }


def response_attribute(response, attribute):
    body = response.content.decode()
    match = re.search(rf'{attribute}="([^"]*)"', body)
    assert match, body
    return html.unescape(match.group(1))


def test_weekly_preview_matches_temporary_library_builder_and_echoes_identity():
    inputs = weekly_inputs()
    response = timeseries_preview(preview_request(inputs))

    assert response.status_code == 200
    assert response_attribute(response, "data-preview-id") == "compute-preview"
    assert response_attribute(response, "data-request-sequence") == "4"
    assert response_attribute(response, "data-success") == "true"
    assert response_attribute(response, "data-status") == ""
    config = json.loads(response_attribute(response, "data-chart-config"))
    expected = ExplainableRecurrentQuantitiesFromWeeklyPattern(inputs).display_quantity.magnitude
    assert config["data"]["labels"][0] == "Mon 00:00"
    assert config["data"]["labels"][-1] == "Sun 23:00"
    assert len(config["data"]["datasets"][0]["data"]) == 168
    np.testing.assert_array_equal(config["data"]["datasets"][0]["data"], expected)


def test_preview_does_not_mutate_request_session():
    request = preview_request(weekly_inputs())
    before = deepcopy(request.session)

    response = timeseries_preview(request)

    assert response.status_code == 200
    assert request.session == before


def test_hourly_preview_returns_bounded_monthly_and_yearly_library_aggregates():
    inputs = hourly_inputs()
    response = timeseries_preview(
        preview_request(
            inputs,
            object_type="UsagePattern",
            field_name="hourly_usage_journey_starts",
            builder="growth",
        )
    )

    assert response.status_code == 200
    assert response_attribute(response, "data-success") == "true"
    configs = json.loads(response_attribute(response, "data-chart-configs"))
    builder = ExplainableHourlyQuantitiesFromFormInputs(inputs)
    expected_total = float(builder.value.sum().magnitude)
    assert set(configs) == {"month", "year"}
    assert len(configs["month"]["data"]["datasets"][0]["data"]) == 24
    assert len(configs["year"]["data"]["datasets"][0]["data"]) == 2
    assert sum(configs["month"]["data"]["datasets"][0]["data"]) == pytest.approx(expected_total, rel=1e-5)
    assert sum(configs["year"]["data"]["datasets"][0]["data"]) == pytest.approx(expected_total, rel=1e-5)
    assert "data-chart-config=" not in response.content.decode()


def test_hourly_preview_aggregates_raw_counts_exactly_across_calendar_boundaries_and_display_prefixes():
    inputs = hourly_inputs(duration_value=1, duration_unit="month")
    inputs.update(
        {
            "start_date": "2024-12-31",
            "initial_volume": 1_000_000_000,
            "initial_volume_timespan": "day",
            "net_growth_rate_in_percentage": 0,
        }
    )

    response = timeseries_preview(
        preview_request(
            inputs,
            object_type="UsagePattern",
            field_name="hourly_usage_journey_starts",
            builder="growth",
        )
    )

    configs = json.loads(response_attribute(response, "data-chart-configs"))
    builder = ExplainableHourlyQuantitiesFromFormInputs(inputs)
    daily_counts = builder.value.magnitude.reshape(-1, 24).sum(axis=1, dtype=np.float64)
    monthly_config = configs["month"]["data"]
    yearly_config = configs["year"]["data"]
    monthly = dict(zip(monthly_config["labels"], monthly_config["datasets"][0]["data"]))
    yearly = dict(zip(yearly_config["labels"], yearly_config["datasets"][0]["data"]))

    assert list(monthly) == ["2024-12", "2025-01"]
    assert monthly["2024-12"] == daily_counts[0]
    assert monthly["2025-01"] == pytest.approx(sum(daily_counts[1:]), rel=0, abs=1e-6)
    assert yearly == {"2024": monthly["2024-12"], "2025": monthly["2025-01"]}
    assert sum(monthly.values()) == pytest.approx(sum(daily_counts), rel=0, abs=1e-6)
    assert sum(monthly.values()) > 1_000_000_000


def test_hourly_preview_reports_invalid_builder_inputs_without_a_chart():
    inputs = hourly_inputs()
    inputs["start_date"] = "not-a-date"

    response = timeseries_preview(
        preview_request(
            inputs,
            object_type="UsagePattern",
            field_name="hourly_usage_journey_starts",
            builder="growth",
        )
    )

    assert response.status_code == 200
    assert response_attribute(response, "data-success") == "false"
    assert "data-chart-configs" not in response.content.decode()


def test_hourly_preview_rejects_duration_beyond_the_form_limit_before_projection():
    response = timeseries_preview(
        preview_request(
            hourly_inputs(duration_value=11),
            object_type="UsagePattern",
            field_name="hourly_usage_journey_starts",
            builder="growth",
        )
    )

    errors = json.loads(response_attribute(response, "data-errors"))
    assert errors[0]["path"] == "modeling_duration_value"
    assert errors[0]["code"] == "invalid_duration"
    assert "data-chart-configs" not in response.content.decode()


def test_registry_allowlist_rejects_unknown_builder():
    response = timeseries_preview(preview_request(weekly_inputs(), builder="import_path.ClassName"))

    assert response.status_code == 400


def test_library_validation_returns_structured_errors_without_chart_replacement():
    inputs = weekly_inputs()
    inputs["profiles"][0]["days"].remove(0)

    response = timeseries_preview(preview_request(inputs))

    assert response.status_code == 200
    assert response_attribute(response, "data-success") == "false"
    errors = json.loads(response_attribute(response, "data-errors"))
    assert errors == [
        {
            "path": "profiles",
            "code": "missing_day_assignment",
            "message": "Day 0 must be assigned to exactly one profile.",
        }
    ]
    assert "data-chart-config" not in response.content.decode()


def test_field_negative_policy_is_derived_server_side():
    inputs = weekly_inputs(baseline=-1, range_value=-2)

    response = timeseries_preview(preview_request(inputs))

    errors = json.loads(response_attribute(response, "data-errors"))
    assert [(error["path"], error["code"]) for error in errors] == [
        ("profiles[0].baseline", "negative_value_not_allowed"),
        ("profiles[0].ranges[0].value", "negative_value_not_allowed"),
    ]


def test_incompatible_unit_is_rejected_from_field_signature():
    inputs = weekly_inputs()
    inputs["unit"] = "GB_ram"

    response = timeseries_preview(preview_request(inputs))

    errors = json.loads(response_attribute(response, "data-errors"))
    assert errors[0]["path"] == "unit"
    assert errors[0]["code"] == "incompatible_unit"


@pytest.mark.parametrize("unit", ["cpu_core", "GB_ram", "GB_stored", "concurrent"])
def test_relationship_dependent_component_need_accepts_only_server_owned_unit_family(unit):
    inputs = weekly_inputs()
    inputs["unit"] = unit

    response = timeseries_preview(
        preview_request(
            inputs,
            object_type="RecurrentEdgeComponentNeed",
            field_name="recurrent_need",
        )
    )

    assert response_attribute(response, "data-success") == "true"


def test_relationship_dependent_component_need_rejects_arbitrary_unit():
    inputs = weekly_inputs()
    inputs["unit"] = "meter"

    response = timeseries_preview(
        preview_request(
            inputs,
            object_type="RecurrentEdgeComponentNeed",
            field_name="recurrent_need",
        )
    )

    errors = json.loads(response_attribute(response, "data-errors"))
    assert errors[0]["path"] == "unit"
    assert errors[0]["code"] == "incompatible_unit"


def test_relationship_dependent_component_need_subclass_rejects_arbitrary_unit():
    inputs = weekly_inputs()
    inputs["unit"] = "meter"

    response = timeseries_preview(
        preview_request(
            inputs,
            object_type="RecurrentEdgeStorageNeed",
            field_name="recurrent_need",
        )
    )

    errors = json.loads(response_attribute(response, "data-errors"))
    assert errors[0]["code"] == "incompatible_unit"
