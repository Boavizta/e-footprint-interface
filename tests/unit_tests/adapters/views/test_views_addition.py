import json
from unittest.mock import MagicMock

import pytest

from model_builder.adapters.repositories import SessionSystemRepository


@pytest.mark.django_db
def test_weekly_validation_error_returns_structured_response_without_mutating_session(
    client, minimal_system_data, monkeypatch
):
    repository = SessionSystemRepository(client.session)
    repository.save_data(minimal_system_data)
    saved_before = repository.get_system_data()
    execute = MagicMock()
    monkeypatch.setattr("model_builder.adapters.views.views_addition.CreateObjectUseCase.execute", execute)
    invalid_pattern = {
        "unit": "cpu_core",
        "profiles": [{"name": "incomplete", "days": [0], "baseline": 1, "ranges": []}],
    }

    response = client.post(
        "/model_builder/add-object/RecurrentEdgeProcess/",
        {
            "type_object_available": "RecurrentEdgeProcess",
            "RecurrentEdgeProcess_name": "Invalid process",
            "RecurrentEdgeProcess_recurrent_compute_needed__weekly_pattern": json.dumps(invalid_pattern),
        },
    )

    assert response.status_code == 422
    assert response.headers["HX-Reswap"] == "none"
    assert response.json()["errors"][0]["code"] == "missing_day_assignment"
    execute.assert_not_called()
    assert SessionSystemRepository(client.session).get_system_data() == saved_before
