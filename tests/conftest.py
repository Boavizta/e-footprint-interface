"""Pytest configuration and shared fixtures."""
import pytest
from efootprint.api_utils.system_to_json import system_to_json

from model_builder.adapters.repositories import InMemorySystemRepository
from model_builder.domain.entities.web_core.model_web import ModelWeb
from tests.fixtures import build_minimal_system


@pytest.fixture
def minimal_system():
    """A minimal complete system with all required objects."""
    return build_minimal_system()


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
