import json
from copy import deepcopy
from io import BytesIO
from unittest.mock import patch

import pytest

from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.repositories.workspace_index import WorkspaceIndex


def _json_upload_file(payload: dict, name: str = "model.json"):
    buffer = BytesIO(json.dumps(payload).encode("utf-8"))
    buffer.name = name
    return buffer


@pytest.mark.django_db
class TestUploadJsonInterfaceConfigPersistence:
    def test_upload_with_matching_model_config_preserves_saved_sankey_config(self, client, minimal_system_data):
        repository = SessionSystemRepository(client.session)
        repository.interface_config = {"sankey_diagrams": [{"id": "deadbeef"}]}
        repository.save_data(minimal_system_data)

        with patch("model_builder.adapters.views.views.SystemImportService.import_system", return_value=minimal_system_data):
            response = client.post(
                "/model_builder/upload-json/",
                {"import-json-input": _json_upload_file(minimal_system_data)},
            )

        assert response.status_code == 302
        saved_data = SessionSystemRepository(client.session).get_system_data()
        assert saved_data["interface_config"] == {"sankey_diagrams": [{"id": "deadbeef"}]}

    def test_upload_without_config_does_not_inherit_replaced_model_guidance(self, client, minimal_system_data):
        session = client.session
        repository = SessionSystemRepository(session)
        repository.interface_config = {"simplified_inputs": {"title": "Old starter", "fields": {}}}
        repository.save_data(minimal_system_data)
        session.save()
        incoming = deepcopy(minimal_system_data)
        incoming.pop("interface_config")
        incoming.pop("efootprint_interface_version")
        response = client.post("/model_builder/upload-json/", {"import-json-input": _json_upload_file(incoming)})
        assert response.status_code == 302
        assert SessionSystemRepository(client.session).interface_config["simplified_inputs"] == {
            "title": "", "guidance": "", "fields": {}}

    def test_upload_with_interface_config_replaces_existing_config_including_card_order(
        self, client, minimal_system_data
    ):
        repository = SessionSystemRepository(client.session)
        repository.interface_config = {"sankey_diagrams": [{"id": "deadbeef"}]}
        repository.save_data(minimal_system_data)

        uploaded_data = {
            **minimal_system_data,
            "interface_config": {
                "sankey_diagrams": [{"id": "cafebabe"}],
                "card_order": {"server-list": ["Server_a", "Server_b"]},
            },
            "efootprint_interface_version": "1.0.0",
        }

        with patch("model_builder.adapters.views.views.SystemImportService.import_system", return_value=uploaded_data):
            response = client.post(
                "/model_builder/upload-json/",
                {"import-json-input": _json_upload_file(uploaded_data)},
            )

        assert response.status_code == 302
        saved_data = SessionSystemRepository(client.session).get_system_data()
        assert saved_data["interface_config"] == {
            "sankey_diagrams": [{"id": "cafebabe"}],
            "card_order": {"server-list": ["Server_a", "Server_b"]},
        }

    def test_invalid_upload_full_render_preserves_the_live_storage_warning(
        self, client, minimal_system_data, settings
    ):
        settings.STORAGES = {
            **settings.STORAGES,
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }
        session = client.session
        SessionSystemRepository(session).save_data(minimal_system_data)
        WorkspaceIndex(session).set_slot_size(0, 4 * 1024 * 1024)
        session.save()
        invalid_file = BytesIO(b"{")
        invalid_file.name = "invalid.json"

        with patch.object(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", 5):
            response = client.post("/model_builder/upload-json/", {"import-json-input": invalid_file})

        content = response.content.decode()
        assert response.status_code == 200
        assert content.count('id="workspace-storage-status"') == 1
        assert "4 MB of 5 MB" in content
        assert "Workspace storage is nearly full" in content
