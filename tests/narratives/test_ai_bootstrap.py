"""The AI-assisted bootstrap, told by its own code (`narrate` and `event` calls) through the real views.

The provider is a local fake: no inference is made. The pages drawn from these tests are
`specs/comprehension-harness/narratives/modeling.html` (`npm run comprehension:render`).
"""
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from django.conf import settings as django_settings

from model_builder.adapters.repositories import SessionWorkspaceRepository
from model_builder.adapters.views import views_ai_bootstrap as views
from model_builder.application.ai_bootstrap.service import Completion
from model_builder.domain.services import is_empty_model
from tests.declare import narrative, planned_test, titled

pytestmark = pytest.mark.django_db
START = "/model_builder/start-ai-bootstrap/"
GENERATE = "/model_builder/generate-ai-bootstrap/"
ANSWER = (Path(django_settings.BASE_DIR) / "ai_sandbox/cases/_handwritten_01_recipe_app.json").read_text()
EDGE_ANSWER = (Path(django_settings.BASE_DIR) / "ai_sandbox/cases/_handwritten_04_ev_charging.json").read_text()
DESCRIPTION = "A recipe app: 200,000 monthly users browse recipes three times a week."


@pytest.fixture(autouse=True)
def configuration(settings, monkeypatch):
    settings.AI_BOOTSTRAP_ENABLED = True
    settings.MISTRAL_API_KEY = "dummy-server-key"
    settings.STORAGES = {**settings.STORAGES, "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
    monkeypatch.setenv("RAISE_EXCEPTIONS", "1")
    monkeypatch.setenv("USE_BOAVIZTAPI_PACKAGE", "1")


@pytest.fixture
def provider(monkeypatch):
    fake = Mock(return_value=Completion(ANSWER, 5000, 800, latency_s=12.5))
    monkeypatch.setattr(views, "complete_mistral", fake)
    return fake


def saved_modeling(client):
    return SessionWorkspaceRepository(client.session).active_repository().get_system_data()


@narrative("The user bootstraps a modeling from a description")
class TestAiBootstrap:
    """Starting with AI empties the active slot and opens a description panel. One provider request is then built
    into a library system, prepared like an import, saved once, and summarized in the response alone."""

    def test_a_description_becomes_a_saved_modeling_summarized_once(self, client, provider):
        started = client.post(START, HTTP_HX_REQUEST="true")
        assert 'data-ai-bootstrap-panel="input"' in started.content.decode()
        assert is_empty_model(saved_modeling(client))

        generated = client.post(GENERATE, {"description": DESCRIPTION})

        assert provider.call_count == 1 and provider.call_args.args[1] == DESCRIPTION
        assert 'data-ai-bootstrap-panel="summary"' in generated.content.decode()
        assert not is_empty_model(saved_modeling(client))
        assert "data-ai-bootstrap-panel" not in client.get("/model_builder/").content.decode()

    def test_a_provider_failure_keeps_the_empty_modeling_and_the_description(self, client, provider):
        provider.side_effect = views.ProviderError("unavailable")
        client.post(START)

        refused = client.post(GENERATE, {"description": DESCRIPTION})

        body = refused.content.decode()
        assert 'data-ai-bootstrap-panel="input"' in body and DESCRIPTION in body
        assert is_empty_model(saved_modeling(client))

    # Extends test_a_provider_failure_keeps_the_empty_modeling_and_the_description, posting Web + edge; no case is added.
    @planned_test("ai-bootstrap-edge#scope-choice: a refused Web + edge generation comes back with Web + edge checked "
                  "beside the description")
    def test_a_refused_generation_keeps_the_scope(self, client, provider):
        pass

    def test_an_answer_outside_the_schema_saves_nothing(self, client, provider):
        provider.return_value = Completion('{"servers": "not a list"}')
        client.post(START)

        refused = client.post(GENERATE, {"description": DESCRIPTION})

        assert 'data-ai-bootstrap-panel="input"' in refused.content.decode()
        assert is_empty_model(saved_modeling(client))

    # @planned ai-bootstrap-edge#scope-selects-format Reads that the provider received the Web + edge instructions.
    # @planned ai-bootstrap-edge#scope-in-request Reads that the summary lists the edge checks after the web ones.
    # @planned ai-bootstrap-edge#edge-device-sizing Reads that the gateway keeps the idle power, reserved RAM and
    # reserved storage the answer states.
    @planned_test("ai-bootstrap-edge#edge-builder: a Web + edge description becomes a modeling with its devices, what they run, "
                  "their deployments and usage spans [edge-scope-builds-edge]")
    def test_a_web_edge_description_becomes_an_edge_modeling(self, client, provider):
        pass

    @planned_test("ai-bootstrap-edge#edge-builder: devices' server calls and the dashboard journey land on one shared server "
                  "[edge-calls-reach-servers]")
    def test_devices_and_people_share_one_server(self, client, provider):
        pass

    @planned_test("ai-bootstrap-edge#edge-builder: devices deployed per building hold their counts per group in each "
                  "deployment [groups-when-relevant]")
    def test_devices_deployed_together_are_grouped(self, client, provider):
        pass

    @planned_test("ai-bootstrap-edge#deployments-over-time: a fleet in service since a past date is deployed from it, its "
                  "devices counted from that date [fleet-as-deployments]")
    def test_a_fleet_in_service_is_deployed_from_the_past(self, client, provider):
        pass

    @planned_test("ai-bootstrap-edge#deployments-over-time: web usage runs from the earliest deployment start, unless dated, until "
                  "the last device retires [shared-period]")
    def test_web_usage_shares_the_deployments_period(self, client, provider):
        pass

    @planned_test("ai-bootstrap-edge#deployments-over-time: generated web and edge usage patterns open with their inputs, and an "
                  "unchanged save keeps them [generated-values-editable]")
    def test_generated_usage_patterns_stay_editable(self, client, provider):
        pass

    @planned_test("ai-bootstrap-edge#edge-builder: a server receives a device's calls once per device deployed, grouped or "
                  "fleet total [calls-scale-with-devices]")
    def test_server_calls_scale_with_deployed_devices(self, client, provider):
        pass

    # @planned ai-bootstrap-edge#scope-in-request Reads that the summary lists no edge check.
    @titled("ai-bootstrap-edge#edge-format: a Web only answer holding edge sections builds no edge object "
            "[web-only-stays-web]")
    def test_a_web_only_answer_builds_no_edge_object(self, client, provider):
        edge_sections = {key: value for key, value in json.loads(EDGE_ANSWER).items() if key.startswith("edge_")}
        provider.return_value = Completion(json.dumps({**json.loads(ANSWER), **edge_sections}))
        client.post(START)

        generated = client.post(GENERATE, {"description": DESCRIPTION, "scope": "web"})

        body = generated.content.decode()
        assert 'data-ai-bootstrap-panel="summary"' in body
        assert all(f"<li>{section}</li>" in body for section in edge_sections)
        assert not any(class_name.startswith("Edge") for class_name in saved_modeling(client))

    @planned_test("ai-bootstrap-edge#scope-choice: Start with AI after a Web + edge generation opens on Web only "
                  "[web-by-default]")
    def test_start_opens_on_web_only(self, client, provider):
        pass
