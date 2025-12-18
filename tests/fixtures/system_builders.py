from model_builder.domain.entities.efootprint_extensions.explainable_hourly_quantities_from_form_inputs import (
    ExplainableHourlyQuantitiesFromFormInputs
)


def create_hourly_usage(
    start_date: str = "2025-01-01",
    duration_value: int = 1,
    duration_unit: str = "year",
    initial_volume: int = 1000,
    volume_timespan: str = "month",
    growth_rate: float = 0,
    growth_timespan: str = "year",
    label: str = "Test hourly usage"
) -> ExplainableHourlyQuantitiesFromFormInputs:
    """Create hourly usage timeseries. No from_defaults exists for this class."""
    form_inputs = {
        "start_date": start_date,
        "modeling_duration_value": duration_value,
        "modeling_duration_unit": duration_unit,
        "initial_volume": initial_volume,
        "initial_volume_timespan": volume_timespan,
        "net_growth_rate_in_percentage": growth_rate,
        "net_growth_rate_timespan": growth_timespan,
    }
    return ExplainableHourlyQuantitiesFromFormInputs(form_inputs=form_inputs, label=label)
