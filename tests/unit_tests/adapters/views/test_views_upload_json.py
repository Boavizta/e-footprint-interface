import json
from io import BytesIO
from unittest.mock import patch

import pytest

from model_builder.adapters.repositories import SessionSystemRepository


def _json_upload_file(payload: dict, name: str = "model.json"):
    buffer = BytesIO(json.dumps(payload).encode("utf-8"))
    buffer.name = name
    return buffer


@pytest.mark.django_db
class TestUploadJsonInterfaceConfigPersistence:
    def test_upload_without_interface_config_preserves_existing_sankey_config(self, client, minimal_system_data):
        repository = SessionSystemRepository(client.session)
        repository.interface_config = {"sankey_diagrams": [{"id": "deadbeef"}]}
        repository.save_data(minimal_system_data)

        with patch("model_builder.adapters.views.views.ProgressiveImportService.import_system", return_value=minimal_system_data):
            response = client.post(
                "/model_builder/upload-json/",
                {"import-json-input": _json_upload_file(minimal_system_data)},
            )

        assert response.status_code == 302
        saved_data = SessionSystemRepository(client.session).get_system_data()
        assert saved_data["interface_config"] == {"sankey_diagrams": [{"id": "deadbeef"}]}

    def test_upload_with_interface_config_replaces_existing_sankey_config(self, client, minimal_system_data):
        repository = SessionSystemRepository(client.session)
        repository.interface_config = {"sankey_diagrams": [{"id": "deadbeef"}]}
        repository.save_data(minimal_system_data)

        uploaded_data = {
            **minimal_system_data,
            "interface_config": {"sankey_diagrams": [{"id": "cafebabe"}]},
            "efootprint_interface_version": "1.0.0",
        }

        with patch("model_builder.adapters.views.views.ProgressiveImportService.import_system", return_value=minimal_system_data):
            response = client.post(
                "/model_builder/upload-json/",
                {"import-json-input": _json_upload_file(uploaded_data)},
            )

        assert response.status_code == 302
        saved_data = SessionSystemRepository(client.session).get_system_data()
        assert saved_data["interface_config"] == {"sankey_diagrams": [{"id": "cafebabe"}]}
