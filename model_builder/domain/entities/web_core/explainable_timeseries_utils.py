import math
from typing import Tuple, Dict, Optional, Callable

import numpy as np
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.utils.display import display_quantity_as_str, best_display_unit, human_readable_unit
from pint import Quantity

from model_builder.domain.entities.web_abstract_modeling_classes.dict_key_web_identity import DictKeyWebIdentity
from model_builder.domain.entities.web_core.model_web_utils import to_rounded_daily_values, reindex_array
from model_builder.domain.entities.web_abstract_modeling_classes.explainable_objects_web import (
    ExplainableObjectWeb,
    ExplainableQuantityWeb,
)

TimeseriesDataPreparer = (
    Callable[[ExplainableHourlyQuantities], Tuple[Dict, Dict]]
    | Callable[[ExplainableRecurrentQuantities], Tuple[Dict, Dict]]
)


def get_web_explainable_from_attr(
    model_web, efootprint_id: str, attr_name: str, id_of_key_in_dict: Optional[str] = None
):
    """Resolve a calculated attribute or one of its dict entries to the concrete web explainable wrapper."""
    edited_web_obj = model_web.get_web_object_from_efootprint_id(efootprint_id)
    web_attr = getattr(edited_web_obj, attr_name)

    if id_of_key_in_dict is None:
        return web_attr

    dict_key = next(
        key for key in web_attr.efootprint_object if DictKeyWebIdentity.from_key(key).matches(id_of_key_in_dict)
    )
    selected_explainable = web_attr.efootprint_object[dict_key]
    web_wrapper = (
        ExplainableQuantityWeb if isinstance(selected_explainable, ExplainableQuantity) else ExplainableObjectWeb
    )

    return web_wrapper(selected_explainable, model_web)


def prepare_timeseries_chart_context(
    model_web,
    efootprint_id: str,
    attr_name: str,
    data_preparer_func: TimeseriesDataPreparer,
    id_of_key_in_dict: Optional[str] = None,
) -> Tuple[Dict, ExplainableObjectWeb]:
    """
    Common logic for preparing timeseries chart context.

    Args:
        model_web: ModelWeb instance
        efootprint_id: ID of the object containing the attribute
        attr_name: Name of the timeseries attribute
        data_preparer_func: Function that converts a raw library timeseries into chart data and extra context
        id_of_key_in_dict: Optional key for dict-based attributes

    Returns:
        (context_dict, web_explainable_object)
    """
    web_explainable = get_web_explainable_from_attr(model_web, efootprint_id, attr_name, id_of_key_in_dict)

    data_dict, extra_context = data_preparer_func(web_explainable.efootprint_object)

    literal_formula, ancestors_mapped_to_symbols_list = (
        web_explainable.compute_literal_formula_and_ancestors_mapped_to_symbols_list()
    )

    context = {
        "web_explainable": web_explainable,
        "data_timeseries": data_dict,
        "literal_formula": literal_formula,
        "ancestors_mapped_to_symbols_list": ancestors_mapped_to_symbols_list,
        **extra_context,
    }

    return context, web_explainable


def prepare_hourly_quantity_data(ehq: ExplainableHourlyQuantities) -> Tuple[Dict, Dict]:
    """Prepare chart data directly from a library hourly timeseries."""
    aggregation_strategy = ehq.plot_aggregation_strategy
    if aggregation_strategy == "sum":
        display_unit = best_display_unit(24 * ehq.value)
    else:
        display_unit = best_display_unit(ehq.value)
    display_value = ehq.value.to(display_unit)
    if ehq.start_date.hour == 0:
        reindexed_values = display_value
        start_date_starting_at_midnight = ehq.start_date
    else:
        start_date_starting_at_midnight = ehq.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        reindexed_values = reindex_array(
            ehq.copy().to(display_unit),
            start_date_starting_at_midnight,
            len(ehq.value) + ehq.start_date.hour,
        )

    n_days = math.ceil(len(reindexed_values) / 24)
    start = np.datetime64(start_date_starting_at_midnight, "D")
    dates = (start + np.arange(n_days)).astype(str).tolist()
    daily_data = to_rounded_daily_values(reindexed_values)
    data_dict = dict(zip(dates, daily_data))

    if aggregation_strategy == "mean":
        aggregation_value = display_quantity_as_str(Quantity(np.mean(daily_data), display_unit))
    elif aggregation_strategy == "sum":
        aggregation_value = display_quantity_as_str(ehq.sum().display_quantity)
    extra_context = {
        "aggregation_strategy": aggregation_strategy,
        "aggregation_value": aggregation_value,
        "display_unit": human_readable_unit(display_unit),
    }
    return data_dict, extra_context


def prepare_hourly_quantity_period_data(ehq: ExplainableHourlyQuantities) -> dict[str, dict[str, float]]:
    """Aggregate raw hourly magnitudes into compact calendar-month and calendar-year series."""
    if ehq.start_date.hour == 0:
        hourly_values = ehq.value
        start_date_starting_at_midnight = ehq.start_date
    else:
        start_date_starting_at_midnight = ehq.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        hourly_values = reindex_array(ehq, start_date_starting_at_midnight, len(ehq.value) + ehq.start_date.hour)

    hours = len(hourly_values)
    day_idx = np.arange(hours) // 24
    n_days = math.ceil(hours / 24)
    daily_sum = np.bincount(day_idx, weights=hourly_values.magnitude, minlength=n_days)
    if ehq.plot_aggregation_strategy == "mean":
        daily_values = daily_sum / np.bincount(day_idx, minlength=n_days)
    else:
        daily_values = daily_sum

    start = np.datetime64(start_date_starting_at_midnight, "D")
    dates = (start + np.arange(n_days)).astype(str).tolist()
    period_data = {"month": {}, "year": {}}
    for date, value in zip(dates, daily_values):
        for granularity, key_length in (("month", 7), ("year", 4)):
            key = date[:key_length]
            period_data[granularity][key] = period_data[granularity].get(key, 0) + float(value)
    return period_data


def weekly_hour_labels() -> list[str]:
    """Return labels for the canonical Monday-first 168-hour week."""
    day_labels = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
    return [f"{day} {hour:02d}:00" for day in day_labels for hour in range(24)]


def prepare_recurrent_quantity_data(
    erq: ExplainableRecurrentQuantities, labels: list[str] | None = None
) -> Tuple[Dict, Dict]:
    """Prepare chart data directly from a library recurrent timeseries."""
    recurrent_values = erq.display_quantity
    chart_labels = labels if labels is not None else [str(hour) for hour in range(len(recurrent_values))]
    if len(chart_labels) != len(recurrent_values):
        raise ValueError("The number of chart labels must match the recurrent timeseries length.")
    data_dict = {label: float(str(val)) for label, val in zip(chart_labels, recurrent_values.magnitude)}

    return data_dict, {"display_unit": human_readable_unit(recurrent_values.units)}
