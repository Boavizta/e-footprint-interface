import math
from datetime import timedelta
from typing import List, Tuple, Dict

import numpy as np
import pytz
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.aggregation_utils import get_plot_aggregation_strategy
from efootprint.constants.units import u
from efootprint.logger import logger


def determine_global_time_bounds(ehqs: List[ExplainableHourlyQuantities]) -> Tuple:
    for ehq in ehqs:
        assert ehq.start_date.tzinfo == pytz.utc, f"Wrong tzinfo for {ehq.label}: {ehq.start_date.tzinfo}"
        if ehq.start_date.hour != 0:
            logger.warning(
                f"{ehq.label} start date doesn't start at midnight: {ehq.start_date}. "
                f"This shouldn't happen if this timeseries has been created with form inputs.")

    global_start = min(ehq.start_date for ehq in ehqs).replace(hour=0, minute=0, second=0, microsecond=0)
    global_end = max(ehq.start_date + timedelta(hours=len(ehq.magnitude) - 1) for ehq in ehqs)
    total_hours = int((global_end - global_start).total_seconds() // 3600) + 1

    return global_start, total_hours


def reindex_array(ehq: ExplainableHourlyQuantities, global_start, total_hours: int) -> u.Quantity:
    offset = int((ehq.start_date - global_start).total_seconds() // 3600)
    vals = ehq.magnitude.astype(np.float32, copy=False)
    padded = np.zeros(total_hours, dtype=np.float32)
    padded[offset: offset + len(vals)] = vals

    return padded * ehq.unit


def get_reindexed_array_from_dict(
    key: str, d: Dict[str, ExplainableHourlyQuantities], global_start, total_hours: int) -> u.Quantity:
    val = d.get(key)
    if isinstance(val, EmptyExplainableObject):
        return np.zeros(total_hours, dtype=np.float32) * u.tonne
    converted_to_tonnes = val.to(u.tonne)

    return reindex_array(converted_to_tonnes, global_start, total_hours)


def to_rounded_daily_values(quantity_arr: u.Quantity, rounding_depth: int = 5) -> List[float]:
    """
    Aggregate hourly values into daily values.

    The aggregation strategy (sum or mean) is automatically determined from the unit:
    - Energy, carbon, data transfer, events → sum
    - CPU, RAM, instances, rates → mean

    Args:
        quantity_arr: Hourly quantity array to aggregate
        rounding_depth: Number of decimal places to round to

    Returns:
        List of daily aggregated values
    """
    hours = len(quantity_arr)
    day_idx = np.arange(hours) // 24
    n_days = math.ceil(hours / 24)
    weights = quantity_arr.magnitude

    aggregation_strategy = get_plot_aggregation_strategy(quantity_arr.units)

    if aggregation_strategy == "mean":
        # For resource allocation metrics (instances, RAM, CPU) - compute mean via sum/count
        # Using bincount for both operations is O(hours) vs O(n_days × hours) with boolean indexing
        daily_sum = np.bincount(day_idx, weights=weights, minlength=n_days)
        daily_count = np.bincount(day_idx, minlength=n_days)
        daily = daily_sum / daily_count
    else:
        # For cumulative metrics (energy, events, data) - sum the values
        daily = np.bincount(day_idx, weights=weights, minlength=n_days)

    return np.round(daily, rounding_depth).tolist()
