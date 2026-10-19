import json
import re
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
        assert 'data-view="simplified"' in first
        assert "Opening help" in first
        assert "simplified_inputs_opening_ids" not in client.session
        again = client.get("/model_builder/", HTTP_HX_REQUEST="true").content.decode()
        assert 'data-view="modeling"' in again
        assert 'data-view="simplified"' not in again

    def patch_bookmarks(self, client, patch, mounted, trigger=None):
        headers = {"HTTP_HX_TRIGGER": trigger} if trigger else {}
        return client.post("/model_builder/patch-simplified-inputs/", {
            "patch": json.dumps(patch), "mounted": json.dumps(mounted), "Storage_storage_capacity": "999999"},
            **headers)

    @staticmethod
    def bookmark_fragments(html):
        """Map each out-of-band bookmark fragment, which starts at its summary, to its bookmark id."""
        return {chunk.split("-summary", 1)[0]: chunk for chunk in html.split('<summary id="')[1:]}

    def test_bookmark_patch_renders_mounted_instances_and_saved_only_on_the_trigger(self, client, minimal_system_data):
        model = self.save_model(client, minimal_system_data)
        server_id = model.servers[0].efootprint_id
        trigger = f"bookmark-{server_id}-server_type-panel"
        companion = f"bookmark-{server_id}-fixed_nb_of_instances-sources"
        mounted = [trigger, f"bookmark-{server_id}-server_type-sources", companion,
                   f"bookmark-{server_id}-lifespan-panel"]
        response = self.patch_bookmarks(client, {"fields": {server_id: {"server_type": {"included": True}}}},
                                        mounted, trigger)
        assert response.status_code == 200
        html = response.content.decode()
        fragments = self.bookmark_fragments(html)
        assert set(fragments) == set(mounted[:3])
        for dom_id, fragment in fragments.items():
            assert 'hx-swap-oob="outerHTML"' in fragment.split("</summary>")[0]
            assert f'<div id="{dom_id}-controls" hx-swap-oob="innerHTML">' in fragment
            assert "Included in Simplified inputs" in fragment
        assert html.count(">Saved</small>") == 1
        assert f'id="{trigger}-status" data-bookmark-status role="status" data-outcome="saved">Saved</small>' in html
        assert "Required by" in fragments[companion].split("</summary>")[0]
        assert re.search(r'data-include-input checked\s+disabled', fragments[companion])
        assert "inverse" not in html and "Undo" not in html

    def test_bookmark_patch_preserves_values_and_retained_help(self, client, minimal_system_data):
        model = self.save_model(client, minimal_system_data)
        owner = model.servers[0].storage.efootprint_id
        bookmark_id = f"bookmark-{owner}-storage_capacity-panel"
        original = deepcopy(SessionSystemRepository(client.session).get_system_data())
        self.patch_bookmarks(client, {"fields": {owner: {"storage_capacity": {"included": True, "help": "Capacity help"}}}},
                             [bookmark_id], bookmark_id)
        response = self.patch_bookmarks(client, {"fields": {owner: {"storage_capacity": {"included": False}}}},
                                        [bookmark_id], bookmark_id)
        fragment = self.bookmark_fragments(response.content.decode())[bookmark_id]
        assert "Not included in Simplified inputs" in fragment
        assert ">Capacity help</textarea>" in fragment
        current = SessionSystemRepository(client.session).get_system_data()
        assert current["Storage"][owner] == original["Storage"][owner]

    def test_bookmark_failure_preserves_workspace_and_selection(self, client, minimal_system_data, monkeypatch):
        monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
        model = self.save_model(client, minimal_system_data)
        server_id = model.servers[0].efootprint_id
        trigger = f"bookmark-{server_id}-fixed_nb_of_instances-panel"
        self.patch_bookmarks(client, {"fields": {server_id: {"server_type": {"included": True}}}}, [])
        original = deepcopy(SessionSystemRepository(client.session).get_system_data())
        response = self.patch_bookmarks(client, {"fields": {server_id: {"fixed_nb_of_instances": {"included": False}}}},
                                        [trigger], trigger)
        assert response.status_code == 422
        assert response["HX-Reswap"] == "none"
        assert "openModalDialog" in response["HX-Trigger-After-Settle"]
        html = response.content.decode()
        assert "closeAndEmptySidePanel()" not in html and "hidePanelResult()" not in html
        assert html.count("data-bookmark-status") == 1
        assert (f'<small id="{trigger}-status" hx-swap-oob="outerHTML" data-bookmark-status role="status" '
                f'data-outcome="rejected">Not saved</small>') in html
        assert "<summary" not in html
        assert SessionSystemRepository(client.session).get_system_data() == original

    @pytest.mark.parametrize("mounted", [None, "not-json"])
    def test_bookmark_patch_without_valid_mounted_ids_is_rejected(
            self, client, minimal_system_data, monkeypatch, mounted):
        monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
        model = self.save_model(client, minimal_system_data)
        before = deepcopy(SessionSystemRepository(client.session).interface_config)
        data = {"patch": json.dumps({"fields": {model.servers[0].efootprint_id: {"lifespan": {"included": True}}}})}
        if mounted is not None:
            data["mounted"] = mounted
        response = client.post("/model_builder/patch-simplified-inputs/", data)
        assert response.status_code == 422
        assert "data-bookmark-status" not in response.content.decode()
        assert SessionSystemRepository(client.session).interface_config == before

    def test_bookmark_controls_are_lazy_for_sources(self, client, minimal_system_data):
        model = self.save_model(client, minimal_system_data)
        html = client.get("/model_builder/source-table/").content.decode()
        assert "data-bookmark" in html and "bookmark-open once" in html
        assert "data-selection-controls" not in html
        owner = model.servers[0].storage.efootprint_id
        response = client.get(f"/model_builder/simplified-input-bookmark/{owner}/storage_capacity/")
        assert "data-selection-controls" in response.content.decode()
        assert "bookmark-" + owner in response.content.decode()

    def test_value_save_targets_one_field_and_both_totals_and_resent_provenance_is_a_no_op(
            self, client, minimal_system_data):
        model = self.save_model(client, minimal_system_data)
        server = model.servers[0]
        original = server.modeling_obj.lifespan
        original.confidence, original.comment = "high", "Reviewed lifespan"
        model.persist_to_cache()
        client.post("/model_builder/save-simplified-inputs/", {"definition": json.dumps({"fields": {
            server.efootprint_id: {"lifespan": {"included": True, "help": ""}, "power": {"included": True, "help": ""}}}})})
        prefix = f"si-{model.system.efootprint_id}-{server.efootprint_id}-lifespan-value"
        endpoint = f"/model_builder/edit-simplified-input/{server.efootprint_id}/lifespan/"
        rendered = self.rendered_inputs(client, server.efootprint_id, "lifespan", prefix)
        assert rendered[prefix + "__source_id"] == "hypothesis"
        response = client.post(endpoint, {**rendered, prefix: "10", "recomputation": "true"})
        content = response.content.decode()
        assert "openModalDialog" not in response["HX-Trigger-After-Settle"]
        assert "simplifiedInputSaved" not in response["HX-Trigger-After-Settle"]
        assert content.count("data-field-address") == 1
        assert 'data-attribute="power"' not in content
        assert content.count("data-quick-total>") == 2
        assert 'id=\'result-block\'' in content
        saved = ModelWeb(SessionSystemRepository(client.session)).servers[0].modeling_obj.lifespan
        assert saved.value.magnitude == 10
        assert saved.source.id == "user_data"
        assert (saved.confidence, saved.comment) == ("high", "Reviewed lifespan")
        before = saved.to_json()
        response = client.post(endpoint, self.rendered_inputs(client, server.efootprint_id, "lifespan", prefix))
        assert self.status(response, prefix) == ("saved", "Saved")
        assert ModelWeb(SessionSystemRepository(client.session)).servers[0].modeling_obj.lifespan.to_json() == before

    @staticmethod
    def rendered_inputs(client, owner_id, attribute, prefix):
        html = client.get(f"/model_builder/simplified-input-field/{owner_id}/{attribute}/").content.decode()
        return InputValues(html, prefix).values

    @staticmethod
    def status(response, prefix):
        match = re.search(rf'id="{prefix.removesuffix("-value")}-save-status"[^>]*?'
                          r'(?: data-outcome="(\w+)")?>([^<]*)</span>', response.content.decode())
        return match.groups() if match else None

    def test_outcome_is_rendered_on_the_submitted_field_only(self, client, minimal_system_data, monkeypatch):
        monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
        model = self.save_model(client, minimal_system_data)
        owner_id = model.servers[0].efootprint_id
        client.post("/model_builder/save-simplified-inputs/", {"definition": json.dumps({"fields": {
            owner_id: {"server_type": {"included": True, "help": ""}}}})})
        prefix = f"si-{model.system.efootprint_id}-{owner_id}"
        endpoint = f"/model_builder/edit-simplified-input/{owner_id}"
        notice = f'<p id="si-{model.system.efootprint_id}-notice" data-simplified-notice role="status" hx-swap-oob="true">'
        response = client.post(endpoint + "/server_type/", {prefix + "-server_type-value": "on-premise"})
        assert notice + "</p>" in response.content.decode()
        count_prefix = prefix + "-fixed_nb_of_instances-value"
        client.post(endpoint + "/fixed_nb_of_instances/", {count_prefix: "1000000", count_prefix + "__unit": "concurrent"})
        response = client.post(endpoint + "/server_type/", {prefix + "-server_type-value": "autoscaling"})
        content = response.content.decode()
        assert content.count("data-field-address") == 2
        assert self.status(response, prefix + "-server_type-value") == ("saved", "Saved")
        assert self.status(response, count_prefix) == (None, "")
        assert re.search(re.escape(notice) + r"[^<]*changed to[^<]*</p>", content)
        assert "simplifiedInputSaved" not in response.get("HX-Trigger-After-Settle", "")
        with patch("model_builder.adapters.views.views_simplified_inputs.present_edited_input",
                   side_effect=ValueError("Presentation failed")):
            response = client.post(endpoint + "/server_type/", {prefix + "-server_type-value": "on-premise"})
        assert response.status_code == 500
        assert self.status(response, prefix + "-server_type-value") == ("rejected", "Not saved")
        assert self.status(response, count_prefix) == (None, "")
        response = client.post(endpoint + "/fixed_nb_of_instances/", {count_prefix: "invalid", count_prefix + "__unit": "concurrent"})
        assert response.status_code == 422
        assert self.status(response, count_prefix) == ("rejected", "Not saved")

    @pytest.mark.parametrize("source_id", ["hypothesis", "automatic_replacement"])
    def test_changed_value_becomes_user_data_and_provenance_only_edit_keeps_its_source(
            self, client, minimal_system_data, source_id):
        from efootprint.abstract_modeling_classes.source_objects import Sources

        model = self.save_model(client, minimal_system_data)
        server = model.servers[0]
        lifespan = server.modeling_obj.lifespan
        lifespan.source = Sources.HYPOTHESIS if source_id == "hypothesis" else Sources.AUTOMATIC_REPLACEMENT
        lifespan.confidence, lifespan.comment = "high", "Replacement history"
        model.persist_to_cache()
        client.post("/model_builder/save-simplified-inputs/", {"definition": json.dumps({"fields": {
            server.efootprint_id: {"lifespan": {"included": True, "help": ""}}}})})
        prefix = f"si-{model.system.efootprint_id}-{server.efootprint_id}-lifespan-value"
        endpoint = f"/model_builder/edit-simplified-input/{server.efootprint_id}/lifespan/"

        def saved():
            return ModelWeb(SessionSystemRepository(client.session)).servers[0].modeling_obj.lifespan

        rendered = self.rendered_inputs(client, server.efootprint_id, "lifespan", prefix)
        client.post(endpoint, {**rendered, prefix + "__comment": "Reviewed history"})
        assert (saved().source.id, saved().confidence, saved().comment) == (source_id, "high", "Reviewed history")
        rendered = self.rendered_inputs(client, server.efootprint_id, "lifespan", prefix)
        client.post(endpoint, {**rendered, prefix: str(saved().value.magnitude + 1)})
        assert (saved().source.id, saved().confidence, saved().comment) == ("user_data", "high", "Reviewed history")

    def test_multiple_select_repeated_keys_save_every_selected_reference(self, client, minimal_system_data):
        from efootprint.core.hardware.device import Device

        fragment = system_to_json(Device.from_defaults("Second device"), save_computed_state=False)
        for key, value in fragment.items():
            if isinstance(value, dict):
                minimal_system_data.setdefault(key, {}).update(value)
        model = self.save_model(client, minimal_system_data)
        pattern = model.system.modeling_obj.usage_patterns[0]
        device_ids = [pattern.devices[0].id, *fragment["Device"]]
        client.post("/model_builder/save-simplified-inputs/", {"definition": json.dumps({"fields": {
            pattern.id: {"devices": {"included": True, "help": ""}}}})})
        prefix = f"si-{model.system.efootprint_id}-{pattern.id}-devices-value"
        response = client.post(f"/model_builder/edit-simplified-input/{pattern.id}/devices/", {prefix: device_ids})
        assert "openModalDialog" not in response.get("HX-Trigger-After-Settle", "")
        saved = ModelWeb(SessionSystemRepository(client.session)).system.modeling_obj.usage_patterns[0]
        assert [device.id for device in saved.devices] == device_ids

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
        assert "data-quick-total>" not in content
        assert "result-block" not in content
        assert content.count("data-field-address") == 1
        assert f'hx-swap-oob="outerHTML:#{prefix.removesuffix("-value")}"' in content
        accepted = client.get(f"/model_builder/simplified-input-field/{server.efootprint_id}/lifespan/")
        assert InputValues(content, prefix).values == InputValues(accepted.content.decode(), prefix).values
        assert SessionSystemRepository(client.session).get_system_data() == before

    def test_expired_model_edit_returns_modal_without_attempting_field_recovery(
            self, client, minimal_system_data, monkeypatch):
        from model_builder.adapters.repositories.cache_backend import CacheBackend

        monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
        model = self.save_model(client, minimal_system_data)
        owner_id = model.servers[0].efootprint_id
        client.post("/model_builder/save-simplified-inputs/", {"definition": json.dumps({"fields": {
            owner_id: {"lifespan": {"included": True, "help": ""}}}})})
        cache_key = f"{SessionSystemRepository.SYSTEM_DATA_KEY}:{client.session.session_key}:0"
        CacheBackend().delete(cache_key)
        response = client.post(f"/model_builder/edit-simplified-input/{owner_id}/lifespan/", {})
        assert response.status_code == 500
        assert response["HX-Reswap"] == "none"
        assert "openModalDialog" in json.loads(response["HX-Trigger-After-Settle"])
        content = response.content.decode()
        assert "Your session has expired" in content
        assert 'id="modal-container" hx-swap-oob="true"' in content
        assert "data-field-address" not in content
        assert "closeAndEmptySidePanel" not in content and "hidePanelResult" not in content

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
        assert "openModalDialog" not in response.get("HX-Trigger-After-Settle", "")
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
        assert "openModalDialog" not in response.get("HX-Trigger-After-Settle", "")
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
        status_id = prefix.removesuffix("-value") + "-save-status"
        assert f'hx-indicator="#{status_id}, [data-quick-total-status]"' in html
        field = client.get(f"/model_builder/simplified-input-field/{owner_id}/hourly_occurrences/").content.decode()
        assert f'id="{status_id}"' in field
        response = client.post(f"/model_builder/edit-simplified-input/{owner_id}/hourly_occurrences/", {
            prefix + "__comment": "Reviewed projection"})
        assert "openModalDialog" not in response.get("HX-Trigger-After-Settle", "")
        html = response.content.decode()
        assert "Edit timeseries" in html and 'data-action="open-source-editor"' in html
        assert "Reviewed projection" in html
        inputs = dict(owner.hourly_occurrences.form_inputs)
        inputs["initial_volume"] = 45
        data = {"UsagePattern_hourly_occurrences__" + key: value for key, value in inputs.items()}
        data["timeseries"] = "true"
        response = client.post(f"/model_builder/edit-simplified-input/{owner_id}/hourly_occurrences/", data)
        assert "openModalDialog" not in response.get("HX-Trigger-After-Settle", "")
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
        data = {} if payload is None else {parameter: payload}
        if endpoint == "patch-simplified-inputs" and payload is not None:
            data["mounted"] = "[]"
        response = client.post(f"/model_builder/{endpoint}/", data)
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
        assert "data-quick-total>" not in content and "result-block" not in content
        assert 'data-attribute="power"' not in content
        accepted = client.get(f"/model_builder/simplified-input-field/{owner_id}/lifespan/")
        values = InputValues(content, prefix).values
        assert values == InputValues(accepted.content.decode(), prefix).values
        assert values[prefix + "__comment"] == current.get("comment", "")

    def test_late_controller_failure_restores_accepted_dependent(self, client, minimal_system_data, monkeypatch):
        from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject

        monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
        model = self.save_model(client, minimal_system_data)
        owner_id = model.servers[0].efootprint_id
        client.post("/model_builder/save-simplified-inputs/", {"definition": json.dumps({"fields": {
            owner_id: {"server_type": {"included": True, "help": ""}}}})})
        prefix = f"si-{model.system.efootprint_id}-{owner_id}"
        endpoint = f"/model_builder/edit-simplified-input/{owner_id}"
        assert client.post(endpoint + "/server_type/", {prefix + "-server_type-value": "on-premise"}).status_code == 200
        count_prefix = prefix + "-fixed_nb_of_instances-value"
        assert client.post(endpoint + "/fixed_nb_of_instances/", {
            count_prefix: "1000000", count_prefix + "__unit": "concurrent"}).status_code == 200
        saved_before = ModelWeb(SessionSystemRepository(client.session)).servers[0].modeling_obj
        assert saved_before.fixed_nb_of_instances.magnitude == 1000000
        with patch("model_builder.adapters.views.views_simplified_inputs.present_edited_input",
                   side_effect=ValueError("Presentation failed")):
            response = client.post(endpoint + "/server_type/", {prefix + "-server_type-value": "autoscaling"})
        saved = ModelWeb(SessionSystemRepository(client.session)).servers[0].modeling_obj
        assert saved.server_type.value == "autoscaling"
        assert isinstance(saved.fixed_nb_of_instances, EmptyExplainableObject)
        assert response.status_code == 500
        content = response.content.decode()
        assert content.count("data-field-address") == 2
        assert f'hx-swap-oob="outerHTML:#{prefix}-fixed_nb_of_instances"' in content
        assert "data-quick-total>" not in content and "result-block" not in content
        accepted = client.get(f"/model_builder/simplified-input-field/{owner_id}/fixed_nb_of_instances/")
        assert InputValues(content, count_prefix).values == InputValues(accepted.content.decode(), count_prefix).values

    def test_bookmark_persistence_value_error_remains_server_error(self, client, minimal_system_data, monkeypatch):
        monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
        model = self.save_model(client, minimal_system_data)
        before = deepcopy(SessionSystemRepository(client.session).interface_config)
        trigger = f"bookmark-{model.servers[0].efootprint_id}-lifespan-panel"
        with patch.object(SessionSystemRepository, "save_interface_config", side_effect=ValueError("Save rejected")):
            response = self.patch_bookmarks(client, {"fields": {
                model.servers[0].efootprint_id: {"lifespan": {"included": True}}}}, [trigger], trigger)
        assert response.status_code == 500
        assert response["HX-Reswap"] == "none"
        assert "openModalDialog" in response["HX-Trigger-After-Settle"]
        html = response.content.decode()
        assert html.count("data-bookmark-status") == 1
        assert f'id="{trigger}-status" hx-swap-oob="outerHTML"' in html and ">Not saved</small>" in html
        assert SessionSystemRepository(client.session).interface_config == before
