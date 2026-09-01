"""Stateless draft previews for editable timeseries builders."""

import json
import math

from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_POST
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.builders.timeseries import WeeklyPatternValidationError
from efootprint.constants.units import u
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.utils.display import human_readable_unit
from efootprint.utils.tools import get_init_signature_params

from model_builder.adapters.forms.timeseries_builder_registry import editable_builders_for
from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.entities.web_core.explainable_timeseries_utils import (
    prepare_hourly_quantity_period_data,
    prepare_recurrent_quantity_data,
    weekly_hour_labels,
)
from model_builder.domain.type_annotation_utils import resolve_optional_annotation


EDGE_COMPONENT_NEED_UNIT_FAMILY = (
    u.cpu_core,
    u.bit_ram,
    u.bit_stored,
    u.concurrent,
)
HOURLY_DURATION_LIMITS = {"month": 120, "year": 10}


def _error(path: str, code: str, message: str) -> dict[str, str]:
    return {"path": path, "code": code, "message": message}


def _resolve_builder(object_type: str, field_name: str, identifier: str):
    modeling_class = MODELING_OBJECT_CLASSES_DICT.get(object_type)
    if modeling_class is None:
        return None, None

    signature = get_init_signature_params(modeling_class)
    if field_name not in signature:
        return None, None
    annotation = resolve_optional_annotation(signature[field_name].annotation)
    definition = next(
        (candidate for candidate in editable_builders_for(annotation) if candidate.identifier == identifier),
        None,
    )
    return modeling_class, definition


def _negative_value_errors(form_inputs: dict) -> list[dict[str, str]]:
    def is_negative(value) -> bool:
        try:
            return float(value) < 0
        except (TypeError, ValueError):
            return False

    errors = []
    if is_negative(form_inputs.get("constant_value", 0)):
        errors.append(
            _error(
                "constant_value",
                "negative_value_not_allowed",
                "Value must be zero or greater for this field.",
            )
        )
    for profile_index, profile in enumerate(form_inputs.get("profiles", [])):
        if is_negative(profile.get("baseline", 0)):
            errors.append(
                _error(
                    f"profiles[{profile_index}].baseline",
                    "negative_value_not_allowed",
                    "Baseline must be zero or greater for this field.",
                )
            )
        for range_index, time_range in enumerate(profile.get("ranges", [])):
            if is_negative(time_range.get("value", 0)):
                errors.append(
                    _error(
                        f"profiles[{profile_index}].ranges[{range_index}].value",
                        "negative_value_not_allowed",
                        "Value must be zero or greater for this field.",
                    )
                )
    return errors


def _hourly_input_errors(form_inputs: dict) -> list[dict[str, str]]:
    errors = []
    duration_unit = form_inputs.get("modeling_duration_unit")
    duration_limit = HOURLY_DURATION_LIMITS.get(duration_unit)
    try:
        duration = float(form_inputs.get("modeling_duration_value"))
    except (TypeError, ValueError):
        duration = math.nan
    if duration_limit is None:
        errors.append(_error("modeling_duration_unit", "invalid_unit", "Duration unit must be month or year."))
    elif not math.isfinite(duration) or duration <= 0 or duration > duration_limit:
        errors.append(
            _error(
                "modeling_duration_value",
                "invalid_duration",
                f"Duration must be greater than 0 and at most {duration_limit} {duration_unit}s.",
            )
        )

    allowed_timespans = {
        "initial_volume_timespan": {"day", "month", "year"},
        "net_growth_rate_timespan": {"month", "year"},
    }
    for field_name, allowed_values in allowed_timespans.items():
        if form_inputs.get(field_name) not in allowed_values:
            errors.append(_error(field_name, "invalid_timespan", f"Invalid {field_name.replace('_', ' ')}."))

    for field_name in ("initial_volume", "net_growth_rate_in_percentage"):
        try:
            value = float(form_inputs.get(field_name))
        except (TypeError, ValueError):
            value = math.nan
        if not math.isfinite(value) or value < 0:
            errors.append(_error(field_name, "invalid_number", "Value must be a finite number that is zero or greater."))
    return errors


def _preview_context(
    preview_id: str, request_sequence: str, errors=None, chart_config=None, chart_configs=None
) -> dict:
    errors = errors or []
    return {
        "preview_id": preview_id,
        "request_sequence": request_sequence,
        "success": not errors,
        "status": (
            ""
            if not errors
            else "Fix the highlighted errors to refresh the preview; the last valid chart is retained."
        ),
        "errors_json": json.dumps(errors),
        "chart_config_json": json.dumps(chart_config) if chart_config is not None else "",
        "chart_configs_json": json.dumps(chart_configs) if chart_configs is not None else "",
    }


def _allowed_units(modeling_class: type, field_name: str) -> tuple:
    """Return server-owned preview units; relationship-specific binding remains a save concern."""
    expected_value = modeling_class.default_values.get(field_name)
    if expected_value is not None:
        return (expected_value.value.units,)
    if field_name == "recurrent_need" and issubclass(modeling_class, RecurrentEdgeComponentNeed):
        return EDGE_COMPONENT_NEED_UNIT_FAMILY
    return ()


@require_POST
def timeseries_preview(request):
    """Render a draft chart response without hydrating or persisting a model."""
    object_type = request.POST.get("object_type", "")
    field_name = request.POST.get("field_name", "")
    builder_identifier = request.POST.get("builder", "")
    preview_id = request.POST.get("preview_id", "")
    request_sequence = request.POST.get("request_sequence", "")
    if not all((object_type, field_name, builder_identifier, preview_id, request_sequence)):
        return HttpResponseBadRequest("Missing preview request identity.")
    try:
        if int(request_sequence) < 1:
            raise ValueError
    except ValueError:
        return HttpResponseBadRequest("Preview request sequence must be a positive integer.")

    modeling_class, definition = _resolve_builder(object_type, field_name, builder_identifier)
    if modeling_class is None or definition is None:
        return HttpResponseBadRequest("Unknown field or timeseries builder.")
    if not issubclass(definition.builder_class, (ExplainableHourlyQuantities, ExplainableRecurrentQuantities)):
        return HttpResponseBadRequest("This timeseries builder is not supported by the preview.")

    try:
        form_inputs = json.loads(request.POST.get("form_inputs", ""))
    except (json.JSONDecodeError, TypeError):
        return HttpResponseBadRequest("Form inputs must be valid JSON.")
    if not isinstance(form_inputs, dict):
        return HttpResponseBadRequest("Form inputs must be a JSON object.")

    if issubclass(definition.builder_class, ExplainableHourlyQuantities):
        errors = _hourly_input_errors(form_inputs)
        if errors:
            context = _preview_context(preview_id, request_sequence, errors=errors)
            return render(request, "model_builder/side_panels/timeseries_preview.html", context)

    try:
        builder = definition.builder_class(form_inputs=form_inputs, label="Draft preview")
    except WeeklyPatternValidationError as validation_error:
        context = _preview_context(preview_id, request_sequence, errors=validation_error.errors)
        return render(request, "model_builder/side_panels/timeseries_preview.html", context)
    except (KeyError, TypeError, ValueError) as validation_error:
        errors = [_error("form_inputs", "invalid_inputs", str(validation_error))]
        context = _preview_context(preview_id, request_sequence, errors=errors)
        return render(request, "model_builder/side_panels/timeseries_preview.html", context)

    errors = []
    if field_name not in modeling_class.attributes_that_can_have_negative_values():
        errors.extend(_negative_value_errors(form_inputs))

    allowed_units = _allowed_units(modeling_class, field_name)
    if allowed_units and not any(builder.value.is_compatible_with(unit) for unit in allowed_units):
        if len(allowed_units) == 1:
            unit_message = f"Unit must be compatible with {human_readable_unit(allowed_units[0])}."
        else:
            allowed_units_label = ", ".join(human_readable_unit(unit) for unit in allowed_units)
            unit_message = f"Unit must be compatible with one of: {allowed_units_label}."
        errors.append(
            _error(
                "unit",
                "incompatible_unit",
                unit_message,
            )
        )
    if errors:
        context = _preview_context(preview_id, request_sequence, errors=errors)
        return render(request, "model_builder/side_panels/timeseries_preview.html", context)

    if isinstance(builder, ExplainableHourlyQuantities):
        period_data = prepare_hourly_quantity_period_data(builder)
        chart_configs = {
            granularity: {
                "type": "bar",
                "data": {
                    "labels": list(values),
                    "datasets": [
                        {
                            "label": "Nb of usage journeys",
                            "borderColor": "#017E7E",
                            "backgroundColor": "#017E7E",
                            "data": list(values.values()),
                            "fill": False,
                        }
                    ],
                },
                "options": {
                    "locale": "en-EN",
                    "responsive": True,
                    "maintainAspectRatio": False,
                    "animation": False,
                    "scales": {
                        "x": {
                            "type": "time",
                            "time": {
                                "unit": granularity,
                                "tooltipFormat": "MMM yyyy" if granularity == "month" else "yyyy",
                            },
                            "title": {"display": False},
                            "grid": {"display": False},
                        },
                        "y": {
                            "display": True,
                            "title": {"display": True, "text": "Number of usage journeys"},
                            "beginAtZero": True,
                        },
                    },
                    "plugins": {
                        "legend": {"display": False},
                        "zoom": {
                            "zoom": {
                                "drag": {"enabled": True},
                                "pinch": {"enabled": True},
                                "mode": "x",
                            }
                        },
                    },
                },
            }
            for granularity, values in period_data.items()
        }
        context = _preview_context(preview_id, request_sequence, chart_configs=chart_configs)
        return render(request, "model_builder/side_panels/timeseries_preview.html", context)

    labels = weekly_hour_labels()
    data, extra = prepare_recurrent_quantity_data(builder, labels)
    chart_config = {
        "type": "line",
        "data": {
            "labels": list(data),
            "datasets": [
                {
                    "label": f"Generated week ({extra['display_unit']})" if extra["display_unit"] else "Generated week",
                    "data": list(data.values()),
                    "borderColor": "#0f766e",
                    "backgroundColor": "rgba(15, 118, 110, 0.12)",
                    "borderWidth": 2,
                    "pointRadius": 0,
                    "stepped": True,
                }
            ],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "animation": False,
            "plugins": {"legend": {"display": False}},
            "scales": {
                "x": {"ticks": {"maxTicksLimit": 7, "maxRotation": 0}},
                "y": {"title": {"display": bool(extra["display_unit"]), "text": extra["display_unit"]}},
            },
        },
    }
    context = _preview_context(preview_id, request_sequence, chart_config=chart_config)
    return render(request, "model_builder/side_panels/timeseries_preview.html", context)
