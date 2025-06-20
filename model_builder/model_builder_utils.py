# interface_utils.py
import math
from datetime import timedelta
from typing import List, Tuple, Dict

import numpy as np
import pytz
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.constants.units import u


def determine_global_time_bounds(
    ehqs: List[ExplainableHourlyQuantities]
) -> Tuple:
    for ehq in ehqs:
        assert ehq.start_date.tzinfo == pytz.utc, (
            f"Mauvais tzinfo pour {ehq.label}: {ehq.start_date.tzinfo}"
        )
        assert ehq.start_date.hour == 0, (
            f"{ehq.label} ne commence pas à minuit: {ehq.start_date}"
        )

    global_start = min(ehq.start_date for ehq in ehqs).replace(hour=0, minute=0, second=0, microsecond=0)
    global_end = max(
        ehq.start_date + timedelta(hours=len(ehq.magnitude) - 1)
        for ehq in ehqs
    )
    total_hours = int((global_end - global_start).total_seconds() // 3600) + 1
    return global_start, total_hours


def reindex_array(
    ehq: ExplainableHourlyQuantities,
    global_start,
    total_hours: int
) -> u.Quantity:
    offset = int((ehq.start_date - global_start).total_seconds() // 3600)
    ehq.to(u.tonne)
    vals = ehq.magnitude.astype(np.float32, copy=False)
    padded = np.zeros(total_hours, dtype=np.float32)
    padded[offset: offset + len(vals)] = vals
    return padded * ehq.unit

def get_quantity_array(
    key: str,
    d: Dict[str, ExplainableHourlyQuantities],
    global_start,
    total_hours: int
) -> u.Quantity:
    val = d.get(key)
    if isinstance(val, EmptyExplainableObject):
        return np.zeros(total_hours, dtype=np.float32) * u.tonne
    return reindex_array(val, global_start, total_hours)

def to_rounded_daily_values(
    quantity_arr: u.Quantity,
    rounding_depth: int = 5
) -> List[float]:
    hours = len(quantity_arr)
    day_idx = np.arange(hours) // 24
    weights = quantity_arr.magnitude
    daily = np.bincount(
        day_idx,
        weights=weights,
        minlength=math.ceil(hours / 24)
    )
    return np.round(daily, rounding_depth).tolist()

def aggregate_daily_ehq(
    ehq: ExplainableHourlyQuantities,
    rounding_depth: int = 5,
) -> Tuple[List[str], List[float]]:
    vals = ehq.magnitude.astype(np.float32)
    n_days = math.ceil(len(vals) / 24)
    daily = np.bincount(
        np.arange(len(vals)) // 24,
        weights=vals,
        minlength=n_days
    )
    daily = np.round(daily, rounding_depth)
    dates = [
        (ehq.start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(n_days)
    ]
    return dates, daily.tolist()
