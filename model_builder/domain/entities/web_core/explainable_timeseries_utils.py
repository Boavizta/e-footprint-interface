import math
from typing import Tuple, Dict, Optional, Callable

import numpy as np

from model_builder.domain.entities.web_core.model_web_utils import to_rounded_daily_values, reindex_array
from model_builder.domain.entities.web_abstract_modeling_classes.explainable_objects_web import ExplainableObjectWeb


def prepare_timeseries_chart_context(
    model_web,
    efootprint_id: str,
    attr_name: str,
    data_preparer_func: Callable,
    id_of_key_in_dict: Optional[str] = None
) -> Tuple[Dict, ExplainableObjectWeb]:
    """
    Common logic for preparing timeseries chart context.

    Args:
        model_web: ModelWeb instance
        efootprint_id: ID of the object containing the attribute
        attr_name: Name of the timeseries attribute
        data_preparer_func: Function to prepare data_dict from web explainable object
        id_of_key_in_dict: Optional key for dict-based attributes

    Returns:
        (context_dict, web_explainable_object)
    """
    edited_web_obj = model_web.get_web_object_from_efootprint_id(efootprint_id)
    web_attr = getattr(edited_web_obj, attr_name)

    if id_of_key_in_dict is None:
        web_explainable = web_attr
    else:
        web_explainable = ExplainableObjectWeb(
            web_attr.efootprint_object[
                model_web.get_efootprint_object_from_efootprint_id(
                    id_of_key_in_dict,
                    "object_type unnecessary because the usage pattern necessarily already belongs to the system")],
            model_web)

    data_dict, extra_context = data_preparer_func(web_explainable)

    literal_formula, ancestors_mapped_to_symbols_list = (
        web_explainable.compute_literal_formula_and_ancestors_mapped_to_symbols_list())

    context = {
        "web_explainable": web_explainable,
        "data_timeseries": data_dict,
        "literal_formula": literal_formula,
        "ancestors_mapped_to_symbols_list": ancestors_mapped_to_symbols_list,
        **extra_context
    }

    return context, web_explainable


def prepare_hourly_quantity_data(web_ehq: ExplainableObjectWeb) -> Tuple[Dict, Dict]:
    """Prepare data for hourly quantity charts."""
    if web_ehq.start_date.hour == 0:
        reindexed_values = web_ehq.value
        start_date_starting_at_midnight = web_ehq.start_date
    else:
        start_date_starting_at_midnight = web_ehq.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        reindexed_values = reindex_array(
            web_ehq, start_date_starting_at_midnight, len(web_ehq.value) + web_ehq.start_date.hour)

    n_days = math.ceil(len(reindexed_values) / 24)
    start = np.datetime64(start_date_starting_at_midnight, "D")
    dates = (start + np.arange(n_days)).astype(str).tolist()
    daily_data = to_rounded_daily_values(reindexed_values)
    data_dict = dict(zip(dates, daily_data))

    extra_context = {"aggregation_strategy": web_ehq.efootprint_object.plot_aggregation_strategy}
    return data_dict, extra_context


def prepare_recurrent_quantity_data(web_erq: ExplainableObjectWeb) -> Tuple[Dict, Dict]:
    """Prepare data for recurrent quantity charts (168-hour canonical week)."""
    recurrent_values = web_erq.value
    hours = list(range(len(recurrent_values)))
    data_dict = {str(hour): float(val) for hour, val in zip(hours, recurrent_values.magnitude)}

    return data_dict, {}
