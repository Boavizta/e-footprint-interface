import json
from copy import deepcopy
from unittest.mock import patch

import pytest
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage

from model_builder.adapters.presenters.simplified_inputs import input_catalog
from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.domain.entities.web_core.model_web import ModelWeb


@pytest.mark.django_db
class TestSimplifiedViews:
    def save_model(self, client, data):
        session = client.session
        SessionSystemRepository(session).save_data(data)
        session.save()
        return ModelWeb(SessionSystemRepository(client.session))

    def test_configure_save_returns_complete_selection_without_changing_model(self, client, minimal_system_data):
        model = self.save_model(client, minimal_system_data)
        server_id = model.servers[0].efootprint_id
        before = deepcopy(SessionSystemRepository(client.session).get_system_data())
        response = client.post("/model_builder/save-simplified-inputs/", {"definition": json.dumps({
            "title": "Author Title", "guidance": "Author Guidance", "fields": {server_id: {
                "server_type": {"included": True, "help": "Choose Type"}}}})})
        assert response.status_code == 200
        content = response.content.decode()
        assert 'data-mode="simplified"' in content
        assert "Choose Type" in content
        assert "Navigation" in content
        assert content.count("data-field-address") == 2
        saved = SessionSystemRepository(client.session).get_system_data()
        for key in ("interface_config", "efootprint_interface_version"):
            saved.pop(key, None)
            before.pop(key, None)
        assert saved == before

    def test_failed_save_keeps_the_target_and_other_panels_and_persisted_settings(
            self, client, minimal_system_data, monkeypatch):
        monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
        model = self.save_model(client, minimal_system_data)
        before = deepcopy(SessionSystemRepository(client.session).interface_config)
        with patch.object(SessionSystemRepository, "save_interface_config", side_effect=ValueError("Save rejected")):
            response = client.post("/model_builder/save-simplified-inputs/", {"definition": json.dumps({
                "fields": {model.servers[0].efootprint_id: {
                    "lifespan": {"included": True, "help": "Keep Draft"}}}})})
        assert response["HX-Reswap"] == "none"
        assert "openModalDialog" in json.loads(response["HX-Trigger-After-Settle"])
        assert "closeAndEmptySidePanel" not in response.content.decode()
        assert "hidePanelResult" not in response.content.decode()
        assert SessionSystemRepository(client.session).interface_config == before

    def test_large_complete_configuration_saves_without_raising_django_parameter_limit(
            self, client, minimal_system_data, settings):
        assert settings.DATA_UPLOAD_MAX_NUMBER_FIELDS == 1000
        for index in range(60):
            server = Server.from_defaults(f"Server {index}", storage=Storage.from_defaults(f"Storage {index}"))
            fragment = system_to_json(server, save_computed_state=False)
            for key, value in fragment.items():
                if isinstance(value, dict):
                    minimal_system_data.setdefault(key, {}).update(value)
        model = self.save_model(client, minimal_system_data)
        fields = {}
        for address, descriptor in input_catalog(model).fields.items():
            if descriptor.eligible:
                fields.setdefault(address.object_id, {})[address.attribute] = {"included": True, "help": "Guidance"}
        assert sum(map(len, fields.values())) > settings.DATA_UPLOAD_MAX_NUMBER_FIELDS
        definition = {"title": "Large model", "guidance": "Complete selection", "fields": fields}
        response = client.post("/model_builder/save-simplified-inputs/", {"definition": json.dumps(definition)})
        assert 'data-mode="simplified"' in response.content.decode()
        assert SessionSystemRepository(client.session).interface_config["simplified_inputs"] == definition

    @pytest.mark.parametrize("definition", ['{"fields":', '[]'])
    def test_invalid_configuration_transport_keeps_saved_definition(
            self, client, minimal_system_data, monkeypatch, definition):
        monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
        self.save_model(client, minimal_system_data)
        before = deepcopy(SessionSystemRepository(client.session).interface_config)
        response = client.post("/model_builder/save-simplified-inputs/", {"definition": definition})
        assert response["HX-Reswap"] == "none"
        assert SessionSystemRepository(client.session).interface_config == before

    def test_json_opening_defaults_are_applied_once_independently_per_slot(self, client, minimal_system_data):
        model = self.save_model(client, minimal_system_data)
        repository = SessionSystemRepository(client.session)
        repository.interface_config = {"simplified_inputs": {"fields": {
            model.servers[0].efootprint_id: {"lifespan": {"included": True, "help": "Opening help"}}}}}
        repository.save_interface_config()
        session = client.session
        session["simplified_inputs_opening_ids"] = [model.system.efootprint_id]
        session.save()
        first = client.get("/model_builder/", HTTP_HX_REQUEST="true").content.decode()
        assert 'data-opening-default="simplified"' in first
        assert "Opening help" in first
        assert "simplified_inputs_opening_ids" not in client.session
        again = client.get("/model_builder/", HTTP_HX_REQUEST="true").content.decode()
        assert "data-opening-default" not in again
