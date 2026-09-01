"""Tests for stateless recurrent-timeseries draft previews."""

import html
import json
import re
from copy import deepcopy

import numpy as np
import pytest
from django.test import RequestFactory
from efootprint.builders.timeseries import ExplainableRecurrentQuantitiesFromWeeklyPattern

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
