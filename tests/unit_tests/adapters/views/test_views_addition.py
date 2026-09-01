from unittest.mock import MagicMock

import pytest
from efootprint.builders.timeseries import WeeklyPatternValidationError

from model_builder.adapters.repositories import SessionSystemRepository


@pytest.mark.django_db
def test_weekly_validation_error_returns_structured_response_without_mutating_session(
    client, minimal_system_data, monkeypatch
):
    repository = SessionSystemRepository(client.session)
    repository.save_data(minimal_system_data)
    saved_before = repository.get_system_data()
    validation_error = WeeklyPatternValidationError(
        [{"path": "profiles[0].ranges[0].start", "code": "invalid_start_hour", "message": "Invalid start."}]
    )
    monkeypatch.setattr(
        "model_builder.adapters.views.views_addition.CreateObjectUseCase.execute",
        MagicMock(side_effect=validation_error),
    )

    response = client.post(
        "/model_builder/add-object/Server/",
        {"type_object_available": "Server", "Server_name": "Invalid server"},
    )

    assert response.status_code == 422
    assert response.headers["HX-Reswap"] == "none"
    assert response.json() == {"errors": validation_error.errors}
    assert SessionSystemRepository(client.session).get_system_data() == saved_before
