from typing import Any

import pytest
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.constants.countries import country_generator, tz
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern

from model_builder.adapters.repositories import InMemorySystemRepository
from model_builder.domain.entities.efootprint_extensions.explainable_hourly_quantities_from_form_inputs import (
    ExplainableHourlyQuantitiesFromFormInputs
)
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.reference_data import DEFAULT_SYSTEM_DATA


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


@pytest.fixture
def minimal_system():
    """A minimal complete system with all required objects."""
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

    system = System("Test System", usage_patterns=[usage_pattern], edge_usage_patterns=[])

    return system


@pytest.fixture
def minimal_system_data(minimal_system) -> dict[str, Any]:
    """System data dict (JSON-serializable) from minimal system."""
    return system_to_json(minimal_system, save_calculated_attributes=False)


@pytest.fixture
def minimal_repository(minimal_system_data):
    """InMemorySystemRepository loaded with minimal system."""
    return InMemorySystemRepository(initial_data=minimal_system_data)


@pytest.fixture
def minimal_model_web(minimal_repository):
    """ModelWeb instance wrapping minimal system."""
    return ModelWeb(minimal_repository)


@pytest.fixture
def empty_repository():
    """Empty InMemorySystemRepository."""
    return InMemorySystemRepository()


@pytest.fixture
def default_system_repository() -> InMemorySystemRepository:
    """Repository loaded with the app's default (empty) system modeling.

    The fixture normalizes data by computing calculated attributes once, so
    integration tests can compare structure after create/edit/delete flows.
    """
    repository = InMemorySystemRepository(initial_data=DEFAULT_SYSTEM_DATA)
    ModelWeb(repository).update_system_data_with_up_to_date_calculated_attributes()
    return repository
