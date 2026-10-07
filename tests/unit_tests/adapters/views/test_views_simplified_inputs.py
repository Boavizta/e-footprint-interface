import json
from copy import deepcopy
from html.parser import HTMLParser
from unittest.mock import patch

import pytest
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage

from model_builder.adapters.presenters.simplified_inputs import input_catalog
from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.domain.entities.web_core.model_web import ModelWeb


class InputValues(HTMLParser):
    def __init__(self, html, prefix):
        super().__init__()
        self.values = {}
        self.prefix = prefix
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        name = attrs.get("name", "")
        if tag == "input" and name.startswith(self.prefix):
            self.values[name] = attrs.get("value", "")


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
        assert response.status_code == 500
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
        assert response.status_code == 422
        assert response["HX-Reswap"] == "none"
        assert 'id="modal-container" hx-swap-oob="true"' in response.content.decode()
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

    def test_bookmark_patch_and_inverse_preserve_values_and_retained_help(self, client, minimal_system_data):
        model = self.save_model(client, minimal_system_data)
        owner = model.servers[0].storage.efootprint_id
        original = deepcopy(SessionSystemRepository(client.session).get_system_data())
        response = client.post("/model_builder/patch-simplified-inputs/", {
            "patch": json.dumps({"fields": {owner: {"storage_capacity": {"included": True, "help": "Capacity help"}}}}),
            "Storage_storage_capacity": "999999"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["fields"][0]["object_id"] == owner
        assert payload["inverse"] == {"fields": {owner: {"storage_capacity": {"included": False}}}}
        response = client.post("/model_builder/patch-simplified-inputs/", {"patch": json.dumps(payload["inverse"])})
        assert response.json()["fields"][0]["setting"] == {"included": False, "help": "Capacity help"}
        current = SessionSystemRepository(client.session).get_system_data()
        assert current["Storage"][owner] == original["Storage"][owner]

    def test_bookmark_failure_preserves_workspace_and_selection(self, client, minimal_system_data, monkeypatch):
        monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
        model = self.save_model(client, minimal_system_data)
        server_id = model.servers[0].efootprint_id
        response = client.post("/model_builder/patch-simplified-inputs/", {"patch": json.dumps({"fields": {
            server_id: {"server_type": {"included": True}}}})})
        fields = response.json()["fields"]
        required = next(field for field in fields if field["attribute"] == "fixed_nb_of_instances")
        assert required["setting"]["included"]
        assert required["required_by"]["attribute"] == "server_type"
        original = deepcopy(SessionSystemRepository(client.session).get_system_data())
        response = client.post("/model_builder/patch-simplified-inputs/", {"patch": json.dumps({"fields": {
            server_id: {"fixed_nb_of_instances": {"included": False}}}})})
        assert response.status_code == 422
        assert response["HX-Reswap"] == "none"
        assert "openModalDialog" in response["HX-Trigger-After-Settle"]
        html = response.content.decode()
        assert "closeAndEmptySidePanel()" not in html and "hidePanelResult()" not in html
        assert SessionSystemRepository(client.session).get_system_data() == original

    def test_bookmark_controls_are_lazy_for_sources(self, client, minimal_system_data):
        model = self.save_model(client, minimal_system_data)
        html = client.get("/model_builder/source-table/").content.decode()
        assert "data-bookmark" in html and "bookmark-open once" in html
        assert "data-selection-controls" not in html
        owner = model.servers[0].storage.efootprint_id
        response = client.get(f"/model_builder/simplified-input-bookmark/{owner}/storage_capacity/")
        assert "data-selection-controls" in response.content.decode()
        assert "bookmark-" + owner in response.content.decode()

    def test_value_save_targets_one_field_and_both_totals_and_preserves_provenance(self, client, minimal_system_data):
        model = self.save_model(client, minimal_system_data)
        server = model.servers[0]
        original = server.modeling_obj.lifespan
        client.post("/model_builder/save-simplified-inputs/", {"definition": json.dumps({"fields": {
            server.efootprint_id: {"lifespan": {"included": True, "help": ""}, "power": {"included": True, "help": ""}}}})})
        prefix = f"si-{model.system.efootprint_id}-{server.efootprint_id}-lifespan-value"
        response = client.post(f"/model_builder/edit-simplified-input/{server.efootprint_id}/lifespan/", {
            prefix: "10", prefix + "__unit": "year", "recomputation": "true"})
        content = response.content.decode()
        assert "openModalDialog" not in response["HX-Trigger-After-Settle"]
        assert content.count("data-field-address") == 1
        assert 'data-attribute="power"' not in content
        assert content.count("data-quick-total>") == 2
        assert 'id=\'result-block\'' in content
        saved = ModelWeb(SessionSystemRepository(client.session)).servers[0].modeling_obj.lifespan
        assert saved.value.magnitude == 10
        assert saved.source.id == original.source.id
        assert saved.confidence == original.confidence
        assert saved.comment == original.comment

    def test_invalid_value_error_restores_editor_and_preserves_panels_and_saved_total(self, client, minimal_system_data, monkeypatch):
        monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
        model = self.save_model(client, minimal_system_data)
        server = model.servers[0]
        client.post("/model_builder/save-simplified-inputs/", {"definition": json.dumps({"fields": {
            server.efootprint_id: {"lifespan": {"included": True, "help": ""}}}})})
        before = deepcopy(SessionSystemRepository(client.session).get_system_data())
        prefix = f"si-{model.system.efootprint_id}-{server.efootprint_id}-lifespan-value"
        response = client.post(f"/model_builder/edit-simplified-input/{server.efootprint_id}/lifespan/", {
            prefix: "invalid", prefix + "__unit": "year"})
        assert response.status_code == 422
        assert response["HX-Reswap"] == "none"
        assert "openModalDialog" in response["HX-Trigger-After-Settle"]
        content = response.content.decode()
        assert "closeAndEmptySidePanel" not in content and "hidePanelResult" not in content
        assert "data-quick-total" not in content
        assert "result-block" not in content
        assert content.count("data-field-address") == 1
        assert f'hx-swap-oob="outerHTML:#{prefix.removesuffix("-value")}"' in content
        accepted = client.get(f"/model_builder/simplified-input-field/{server.efootprint_id}/lifespan/")
        assert InputValues(content, prefix).values == InputValues(accepted.content.decode(), prefix).values
        assert SessionSystemRepository(client.session).get_system_data() == before

    def test_large_selected_model_value_save_builds_only_affected_editor(self, client, minimal_system_data):
        from model_builder.adapters.forms.form_context_builder import FormContextBuilder
        from model_builder.application.use_cases.simplified_inputs import UpdateSimplifiedDefinitionUseCase

        for index in range(60):
            server = Server.from_defaults(f"Server {index}", storage=Storage.from_defaults(f"Storage {index}"))
            fragment = system_to_json(server, save_computed_state=False)
            for key, value in fragment.items():
                if isinstance(value, dict):
                    minimal_system_data.setdefault(key, {}).update(value)
        model = self.save_model(client, minimal_system_data)
        definition = {"fields": {server.efootprint_id: {"lifespan": {"included": True, "help": ""}}
                                 for server in model.servers}}
        UpdateSimplifiedDefinitionUseCase(model.repository, input_catalog(model)).execute(definition, replace=True)
        owner_id = model.servers[0].efootprint_id
        prefix = f"si-{model.system.efootprint_id}-{owner_id}-lifespan-value"
        original = FormContextBuilder.build_input_fields
        calls = []

        def build_fields(builder, owner, attributes):
            calls.append((owner.efootprint_id, attributes))
            return original(builder, owner, attributes)

        with patch.object(FormContextBuilder, "build_input_fields", build_fields):
            response = client.post(f"/model_builder/edit-simplified-input/{owner_id}/lifespan/", {
                prefix: "10", prefix + "__unit": "year"})
        assert "openModalDialog" not in response["HX-Trigger-After-Settle"]
        assert calls == [(owner_id, {"lifespan"})]
        assert response.content.decode().count("data-field-address") == 1

    def test_blank_optional_count_remains_empty_with_accepted_comment(self, client, minimal_system_data):
        from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject

        model = self.save_model(client, minimal_system_data)
        owner_id = model.servers[0].efootprint_id
        client.post("/model_builder/save-simplified-inputs/", {"definition": json.dumps({"fields": {
            owner_id: {"fixed_nb_of_instances": {"included": True, "help": ""}}}})})
        prefix = f"si-{model.system.efootprint_id}-{owner_id}-fixed_nb_of_instances-value"
        response = client.post(f"/model_builder/edit-simplified-input/{owner_id}/fixed_nb_of_instances/", {
            prefix: "", prefix + "__unit": "dimensionless", prefix + "__comment": "Automatic fleet size"})
        assert "openModalDialog" not in response["HX-Trigger-After-Settle"]
        count = ModelWeb(SessionSystemRepository(client.session)).servers[0].modeling_obj.fixed_nb_of_instances
        assert isinstance(count, EmptyExplainableObject)
        assert count.comment == "Automatic fleet size"

    def test_focused_timeseries_reuses_value_parser_and_outside_metadata_save(self, client, minimal_system_data):
        model = self.save_model(client, minimal_system_data)
        owner = model.system.modeling_obj.usage_patterns[0]
        owner_id = owner.id
        client.post("/model_builder/save-simplified-inputs/", {"definition": json.dumps({"fields": {
            owner_id: {"hourly_occurrences": {"included": True, "help": "Projection guidance"}}}})})
        response = client.get(f"/model_builder/simplified-timeseries-panel/{owner_id}/hourly_occurrences/")
        html = response.content.decode()
        assert html.count("data-hourly-timeseries-preview") == 1
        assert "data-simplified-timeseries" in html
        assert "data-bookmark" not in html
        assert "__source_id" not in html
        prefix = f"si-{model.system.efootprint_id}-{owner_id}-hourly_occurrences-value"
        response = client.post(f"/model_builder/edit-simplified-input/{owner_id}/hourly_occurrences/", {
            prefix + "__comment": "Reviewed projection"})
        assert "openModalDialog" not in response["HX-Trigger-After-Settle"]
        html = response.content.decode()
        assert "Edit timeseries" in html and 'data-action="open-source-editor"' in html
        assert "Reviewed projection" in html
        inputs = dict(owner.hourly_occurrences.form_inputs)
        inputs["initial_volume"] = 45
        data = {"UsagePattern_hourly_occurrences__" + key: value for key, value in inputs.items()}
        data["timeseries"] = "true"
        response = client.post(f"/model_builder/edit-simplified-input/{owner_id}/hourly_occurrences/", data)
        assert "openModalDialog" not in response["HX-Trigger-After-Settle"]
        current = ModelWeb(SessionSystemRepository(client.session)).system.modeling_obj.usage_patterns[0]
        assert current.hourly_occurrences.form_inputs["initial_volume"] == "45"
        assert current.hourly_occurrences.comment == "Reviewed projection"
        saved = client.get(f"/model_builder/simplified-input-field/{owner_id}/hourly_occurrences/").content.decode()
        assert "data-simplified-editor" in saved and "Reviewed projection" in saved

    def test_timeseries_panel_rejects_unselected_and_non_timeseries_inputs(self, client, minimal_system_data, monkeypatch):
        monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
        model = self.save_model(client, minimal_system_data)
        server_id = model.servers[0].efootprint_id
        response = client.get(f"/model_builder/simplified-timeseries-panel/{server_id}/lifespan/")
        assert "openModalDialog" in response["HX-Trigger-After-Settle"]
        client.post("/model_builder/save-simplified-inputs/", {"definition": json.dumps({"fields": {
            server_id: {"lifespan": {"included": True, "help": ""}}}})})
        response = client.get(f"/model_builder/simplified-timeseries-panel/{server_id}/lifespan/")
        assert "openModalDialog" in response["HX-Trigger-After-Settle"]


    @pytest.mark.parametrize("endpoint,parameter", [
        ("save-simplified-inputs", "definition"), ("patch-simplified-inputs", "patch"),
    ])
    @pytest.mark.parametrize("payload", [None, "not-json", '{"fields": {"unknown": {"power": {"included": true}}}}'])
    def test_definition_validation_has_error_status_and_oob_modal(
            self, client, minimal_system_data, monkeypatch, endpoint, parameter, payload):
        monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
        self.save_model(client, minimal_system_data)
        before = deepcopy(SessionSystemRepository(client.session).get_system_data())
        response = client.post(f"/model_builder/{endpoint}/", {} if payload is None else {parameter: payload})
        assert response.status_code == 422
        assert response["HX-Reswap"] == "none"
        assert 'id="modal-container" hx-swap-oob="true"' in response.content.decode()
        assert "openModalDialog" in response["HX-Trigger-After-Settle"]
        assert SessionSystemRepository(client.session).get_system_data() == before

    @pytest.mark.parametrize("failure_boundary", ["update", "persist", "present"])
    @pytest.mark.parametrize("metadata_only", [False, True])
    def test_rejected_inline_edit_restores_fresh_repository_value_and_provenance(
            self, client, minimal_system_data, monkeypatch, failure_boundary, metadata_only):
        from model_builder.domain.exceptions import InputValidationError

        monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
        model = self.save_model(client, minimal_system_data)
        owner_id = model.servers[0].efootprint_id
        client.post("/model_builder/save-simplified-inputs/", {"definition": json.dumps({"fields": {
            owner_id: {"lifespan": {"included": True, "help": ""}, "power": {"included": True, "help": ""}}}})})
        before = ModelWeb(SessionSystemRepository(client.session)).servers[0].modeling_obj.lifespan.to_json()
        prefix = f"si-{model.system.efootprint_id}-{owner_id}-lifespan-value"
        payload = {} if metadata_only else {prefix: "10", prefix + "__unit": "year"}
        payload.update({prefix + "__confidence": "high", prefix + "__comment": "Submitted comment",
                        prefix + "__source_name": "Submitted report", prefix + "__source_link": "https://example.test/report"})
        payload["recomputation"] = "true"
        target = {
            "update": "model_builder.adapters.views.views_simplified_inputs.EditSimplifiedInputUseCase.execute",
            "persist": "model_builder.domain.entities.web_core.model_web.ModelWeb.persist_to_cache",
            "present": "model_builder.adapters.views.views_simplified_inputs.present_edited_input",
        }[failure_boundary]
        error = InputValidationError("Edit rejected") if failure_boundary == "update" else ValueError("Save failure")
        with patch(target, side_effect=error):
            response = client.post(f"/model_builder/edit-simplified-input/{owner_id}/lifespan/", payload)
        saved = ModelWeb(SessionSystemRepository(client.session)).servers[0].modeling_obj.lifespan
        current = saved.to_json()
        if failure_boundary == "present":
            assert current["comment"] == "Submitted comment"
            assert current["confidence"] == "high"
            assert saved.source.name == "Submitted report"
            assert current["value"] == (before["value"] if metadata_only else 10)
        else:
            assert current == before
        assert response.status_code == (422 if failure_boundary == "update" else 500)
        assert response["HX-Reswap"] == "none"
        content = response.content.decode()
        assert 'id="modal-container" hx-swap-oob="true"' in content
        assert "closeAndEmptySidePanel" not in content and "hidePanelResult" not in content
        assert content.count("data-field-address") == 1
        assert f'hx-swap-oob="outerHTML:#{prefix.removesuffix("-value")}"' in content
        assert "data-quick-total" not in content and "result-block" not in content
        assert 'data-attribute="power"' not in content
        accepted = client.get(f"/model_builder/simplified-input-field/{owner_id}/lifespan/")
        values = InputValues(content, prefix).values
        assert values == InputValues(accepted.content.decode(), prefix).values
        assert values[prefix + "__comment"] == current.get("comment", "")

    def test_bookmark_persistence_value_error_remains_server_error(self, client, minimal_system_data, monkeypatch):
        monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
        model = self.save_model(client, minimal_system_data)
        before = deepcopy(SessionSystemRepository(client.session).interface_config)
        with patch.object(SessionSystemRepository, "save_interface_config", side_effect=ValueError("Save rejected")):
            response = client.post("/model_builder/patch-simplified-inputs/", {"patch": json.dumps({"fields": {
                model.servers[0].efootprint_id: {"lifespan": {"included": True}}}})})
        assert response.status_code == 500
        assert response["HX-Reswap"] == "none"
        assert "openModalDialog" in response["HX-Trigger-After-Settle"]
        assert SessionSystemRepository(client.session).interface_config == before
