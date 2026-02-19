import json
from pathlib import Path

import pytest
from efootprint import __version__ as efootprint_version

from model_builder.adapters.repositories import InMemorySystemRepository
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.reference_data import DEFAULT_SYSTEM_DATA


@pytest.fixture
def legacy_v9_system_data() -> dict:
    repo_root = Path(__file__).parents[0]
    legacy_path = repo_root / "legacy_v9_default_system_data.json"
    return json.loads(legacy_path.read_text(encoding="utf-8"))


def test_default_reference_system_data_has_current_efootprint_version():
    assert DEFAULT_SYSTEM_DATA["efootprint_version"] == efootprint_version


def test_legacy_v9_system_data_is_upgraded_and_persisted_with_current_efootprint_version(legacy_v9_system_data):
    assert legacy_v9_system_data["efootprint_version"] == "9.1.4"

    repository = InMemorySystemRepository(initial_data=legacy_v9_system_data)
    model_web = ModelWeb(repository)

    if efootprint_version != model_web.initial_system_data_efootprint_version:
        model_web.update_system_data_with_up_to_date_calculated_attributes()

    saved_system_data = repository.get_system_data()
    assert saved_system_data is not None
    assert saved_system_data["efootprint_version"] == efootprint_version
    assert "Device" in saved_system_data
