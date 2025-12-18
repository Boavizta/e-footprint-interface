"""Pytest configuration and shared fixtures."""
import pytest
from efootprint.api_utils.system_to_json import system_to_json
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
from model_builder.domain.entities.web_core.model_web import ModelWeb
from tests.fixtures.system_builders import create_hourly_usage


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
def minimal_system_data(minimal_system):
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
