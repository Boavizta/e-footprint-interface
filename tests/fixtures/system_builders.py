"""Builders for creating e-footprint systems for testing.

Uses from_defaults pattern directly. For simple objects, use from_defaults in tests:
    Device.from_defaults("Test Device")
    Server.from_defaults("Test Server", storage=storage)

This module only provides helpers that create complex connected structures.
"""
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.constants.countries import country_generator, tz
from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.device import Device
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.system import System

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


def build_minimal_system(name: str = "Test System") -> System:
    """Build a minimal complete system with all required objects connected.

    Creates: storage -> server -> job -> uj_step -> uj -> usage_pattern -> system
    This is useful when you need a valid system but don't care about specific objects.
    """
    storage = Storage.from_defaults("Test Storage")
    server = Server.from_defaults("Test Server", storage=storage)
    job = Job.from_defaults("Test Job", server=server)
    uj_step = UsageJourneyStep.from_defaults("Test Step", jobs=[job])
    uj = UsageJourney("Test Journey", uj_steps=[uj_step])

    usage_pattern = UsagePattern(
        "Test Usage Pattern",
        usage_journey=uj,
        devices=[Device.from_defaults("Test Device")],
        network=Network.from_defaults("Test Network"),
        country=country_generator("Test Country", "TST", SourceValue(100 * u.g / u.kWh), tz('Europe/Paris'))(),
        hourly_usage_journey_starts=create_hourly_usage()
    )

    return System(name, usage_patterns=[usage_pattern], edge_usage_patterns=[])
