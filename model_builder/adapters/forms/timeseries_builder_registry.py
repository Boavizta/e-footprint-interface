"""Interface-owned registry of timeseries builders that can be edited in forms."""

from dataclasses import dataclass
from typing import Callable

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.builders.timeseries import (
    ExplainableHourlyQuantitiesFromFormInputs,
    ExplainableRecurrentQuantitiesFromConstant,
    ExplainableRecurrentQuantitiesFromWeeklyPattern,
)


@dataclass(frozen=True)
class TimeseriesBuilderDefinition:
    """UI metadata and draft initialization for one editable library builder."""

    identifier: str
    label: str
    template_name: str
    builder_class: type
    default_inputs: Callable[[object], dict]


def _existing_inputs_or_empty(value, builder_class: type) -> dict:
    return value.form_inputs if isinstance(value, builder_class) else {}


def _constant_inputs(value) -> dict:
    existing = _existing_inputs_or_empty(value, ExplainableRecurrentQuantitiesFromConstant)
    if existing:
        return dict(existing)

    magnitude = float(value.value.magnitude[0])
    return {"constant_value": magnitude, "constant_unit": f"{value.value.units:~P}"}


def _weekly_inputs(value) -> dict:
    existing = _existing_inputs_or_empty(value, ExplainableRecurrentQuantitiesFromWeeklyPattern)
    if existing:
        return existing

    constant = _constant_inputs(value)
    baseline = float(constant["constant_value"])
    return {
        "unit": constant["constant_unit"],
        "profiles": [
            {"name": "weekday", "days": [0, 1, 2, 3, 4], "baseline": baseline, "ranges": []},
            {"name": "weekend", "days": [5, 6], "baseline": baseline, "ranges": []},
        ],
    }


def _hourly_inputs(value) -> dict:
    return dict(_existing_inputs_or_empty(value, ExplainableHourlyQuantitiesFromFormInputs))


EDITABLE_TIMESERIES_BUILDERS = {
    ExplainableHourlyQuantities: (
        TimeseriesBuilderDefinition(
            identifier="growth",
            label="Growth projection",
            template_name="hourly_quantities_from_growth.html",
            builder_class=ExplainableHourlyQuantitiesFromFormInputs,
            default_inputs=_hourly_inputs,
        ),
    ),
    ExplainableRecurrentQuantities: (
        TimeseriesBuilderDefinition(
            identifier="constant",
            label="Constant value",
            template_name="recurrent_quantities_from_constant.html",
            builder_class=ExplainableRecurrentQuantitiesFromConstant,
            default_inputs=_constant_inputs,
        ),
        TimeseriesBuilderDefinition(
            identifier="weekly_pattern",
            label="Weekly pattern",
            template_name="recurrent_quantities_from_weekly_pattern.html",
            builder_class=ExplainableRecurrentQuantitiesFromWeeklyPattern,
            default_inputs=_weekly_inputs,
        ),
    ),
}


def editable_builders_for(annotation: type) -> tuple[TimeseriesBuilderDefinition, ...]:
    """Return the ordered editable builders registered for an explainable timeseries base type."""
    return EDITABLE_TIMESERIES_BUILDERS.get(annotation, ())


def build_timeseries_form_config(annotation: type, value) -> dict | None:
    """Build template data for a registered value, or ``None`` when it is read-only."""
    builders = editable_builders_for(annotation)
    selected = next((builder for builder in builders if isinstance(value, builder.builder_class)), None)
    if selected is None:
        return None

    return {
        "selected_builder": selected.identifier,
        "show_builder_selector": len(builders) > 1,
        "builders": [
            {
                "identifier": builder.identifier,
                "label": builder.label,
                "template_name": builder.template_name,
                "default": builder.default_inputs(value),
            }
            for builder in builders
        ],
    }
