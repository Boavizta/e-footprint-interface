"""The AI-assisted bootstrap, told by its own code (`narrate` and `event` calls) through the real views.

The provider is a local fake: no inference is made. The pages drawn from these tests are
`specs/comprehension-harness/narratives/modeling.html` (`npm run comprehension:render`).
"""
import json
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import Mock

import pytest
from django.conf import settings as django_settings
from efootprint.constants.units import u

from model_builder.adapters.repositories import SessionWorkspaceRepository
from model_builder.adapters.views import views_ai_bootstrap as views
from model_builder.application.ai_bootstrap.service import Completion
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.services import is_empty_model
from tests.declare import narrative, planned_test, titled

pytestmark = pytest.mark.django_db
START = "/model_builder/start-ai-bootstrap/"
GENERATE = "/model_builder/generate-ai-bootstrap/"
CASES = Path(django_settings.BASE_DIR) / "ai_sandbox/cases"
ANSWER = (CASES / "_handwritten_01_recipe_app.json").read_text()
BUILDING_ANSWER = (CASES / "_handwritten_03_smart_building.json").read_text()  # grouped devices, one past start
EDGE_ANSWER = (CASES / "_handwritten_04_ev_charging.json").read_text()  # fleet totals, two countries
DESCRIPTION = "A recipe app: 200,000 monthly users browse recipes three times a week."
WEB_YEAR_START = datetime(2027, 1, 1, tzinfo=timezone.utc)


def at_web_year_start(series):
    """The value of an hourly series in the first hour of 2027, the "today" of the descriptions."""
    start = series.start_date if series.start_date.tzinfo else series.start_date.replace(tzinfo=timezone.utc)
    return float(series.value.magnitude[int((WEB_YEAR_START - start) / timedelta(hours=1))])


def library_system(client):
    return ModelWeb(SessionWorkspaceRepository(client.session).active_repository()).system.modeling_obj


def edge_device(system, name):
    return next(device for device in system.edge_devices if device.name == name)


def server_needs(pattern):
    return [need for journey in pattern.edge_usage_journeys for function in journey.edge_functions
            for need in function.recurrent_server_needs]


class HourlyEditorInputs(HTMLParser):
    """What the hourly editor of an edit panel opens with: its inputs' values and its selects' selected options."""

    def __init__(self, panel: str):
        super().__init__()
        self.values, self._select = {}, None
        self.feed(panel)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "option" and self._select and "selected" in attrs:
            self.values[self._select] = attrs["value"]
        elif "data-hourly-preview-input" in attrs:
            if tag == "input":
                self.values[attrs["name"]] = attrs.get("value", "")
            elif tag == "select":
                self._select = attrs["name"]

    def handle_endtag(self, tag):
        if tag == "select":
            self._select = None


def as_numbers(form_inputs: dict) -> dict:
    """Form inputs compared as the editor reads them: a number posted as text is the same number."""
    numbers = {}
    for key, value in form_inputs.items():
        try:
            numbers[key] = float(value)
        except (TypeError, ValueError):
            numbers[key] = value
    return numbers


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


def generate_web_edge(client, provider, answer: str):
    provider.return_value = Completion(answer)
    client.post(START)
    return client.post(GENERATE, {"description": DESCRIPTION, "scope": "web_edge"})


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

    @titled("ai-bootstrap-edge#edge-builder: a Web + edge description becomes a modeling with its devices, what they run, "
            "their deployments and usage spans [edge-scope-builds-edge]")
    def test_a_web_edge_description_becomes_an_edge_modeling(self, client, provider):
        generated = generate_web_edge(client, provider, BUILDING_ANSWER)

        assert "edge_devices" in provider.call_args.args[0]
        panel = generated.content.decode().split('data-ai-bootstrap-panel="summary"')[1]
        assert panel.index("Infrastructure:") < panel.index("Deployments:") < panel.index("Server calls:")
        system = library_system(client)
        assert {device.name for device in system.edge_devices} == {"Gateway", "Wireless sensor"}
        gateway = edge_device(system, "Gateway")
        assert gateway.idle_power.value == 3 * u.W and gateway.base_ram_consumption.value == 1 * u.GB_ram
        assert gateway.storage.base_storage_need.value == 8 * u.GB_stored
        [deployment] = system.edge_usage_patterns
        assert {function.name for journey in deployment.edge_usage_journeys for function in journey.edge_functions} == {
            "Aggregate and upload telemetry", "Sense every minute"}
        starts = deployment.hourly_deployment_starts.form_inputs
        assert (starts["initial_volume"], starts["initial_volume_timespan"]) == (60, "month")
        assert deployment.usage_span.value == 5 * u.year

    @titled("ai-bootstrap-edge#edge-builder: devices' server calls and the dashboard journey land on one shared server "
            "[edge-calls-reach-servers]")
    def test_devices_and_people_share_one_server(self, client, provider):
        generate_web_edge(client, provider, BUILDING_ANSWER)

        system = library_system(client)
        [upload] = server_needs(system.edge_usage_patterns[0])
        called = {job.server.name for job in upload.jobs}
        dashboard = next(journey for journey in system.usage_journeys if journey.name == "Facility manager checks dashboard")
        assert called == {"Ingestion API", "Time-series DB"}
        assert called == {job.server.name for step in dashboard.uj_steps for job in step.jobs}
        assert len(system.servers) == 3

    @titled("ai-bootstrap-edge#edge-builder: devices deployed per building hold their counts per group in each "
            "deployment [groups-when-relevant]")
    def test_devices_deployed_together_are_grouped(self, client, provider):
        generate_web_edge(client, provider, BUILDING_ANSWER)

        system = library_system(client)
        gateway, sensor = edge_device(system, "Gateway"), edge_device(system, "Wireless sensor")
        [building] = sensor.parent_groups
        assert building.name == "Equipped building" and building.parent_groups == []
        assert building.edge_device_counts[gateway].value == 1 * u.dimensionless
        assert building.edge_device_counts[sensor].value == 40 * u.dimensionless
        assert sensor.total_nb_of_units.value == 40 * u.dimensionless
        assert at_web_year_start(system.edge_usage_patterns[0].nb_deployments_in_parallel) == pytest.approx(1500, rel=0.05)

    @titled("ai-bootstrap-edge#deployments-over-time: a fleet in service since a past date is deployed from it, its "
            "devices counted from that date [fleet-as-deployments]")
    def test_a_fleet_in_service_is_deployed_from_the_past(self, client, provider):
        generate_web_edge(client, provider, EDGE_ANSWER)

        system = library_system(client)
        germany = next(pattern for pattern in system.edge_usage_patterns if pattern.name == "Stations in Germany")
        starts = germany.hourly_deployment_starts
        assert starts.form_inputs["start_date"] == "2024-01-01"
        assert (starts.form_inputs["modeling_duration_value"], starts.form_inputs["modeling_duration_unit"]) == (4, "year")
        assert (starts.form_inputs["initial_volume"], starts.form_inputs["initial_volume_timespan"]) == (75, "month")
        assert "75 a month since January 2024" in starts.comment
        assert at_web_year_start(germany.nb_deployments_in_parallel) == pytest.approx(2700, rel=0.05)

    @titled("ai-bootstrap-edge#deployments-over-time: web usage runs from the earliest deployment start, unless dated, until "
            "the last device retires [shared-period]")
    def test_web_usage_shares_the_deployments_period(self, client, provider):
        generate_web_edge(client, provider, EDGE_ANSWER)
        [team] = library_system(client).usage_patterns
        inputs = team.hourly_occurrences.form_inputs
        assert inputs["start_date"] == "2024-01-01"  # the deployments' start: 2,700 stations since 2024
        assert (inputs["modeling_duration_value"], inputs["modeling_duration_unit"]) == (12, "year")  # to 2035, 8 years after the last station

        dated = json.loads(EDGE_ANSWER)
        dated["usage_patterns"][0]["start_date"] = "2026-06-01"
        generate_web_edge(client, provider, json.dumps(dated))

        system = library_system(client)
        inputs = system.usage_patterns[0].hourly_occurrences.form_inputs
        assert inputs["start_date"] == "2026-06-01"
        assert (inputs["modeling_duration_value"], inputs["modeling_duration_unit"]) == (117, "month")
        assert {pattern.hourly_deployment_starts.form_inputs["start_date"] for pattern in system.edge_usage_patterns} == {"2024-01-01"}

    @titled("ai-bootstrap-edge#deployments-over-time: generated web and edge usage patterns open with their inputs, and an "
            "unchanged save keeps them [generated-values-editable]")
    def test_generated_usage_patterns_stay_editable(self, client, provider):
        generate_web_edge(client, provider, BUILDING_ANSWER)
        system = library_system(client)
        managers = next(pattern for pattern in system.usage_patterns if pattern.name == "Managers in France")
        [buildings] = system.edge_usage_patterns

        for kind, pattern, attribute in (("UsagePattern", managers, "hourly_occurrences"),
                                         ("EdgeUsagePattern", buildings, "hourly_deployment_starts")):
            generated_inputs = getattr(pattern, attribute).form_inputs
            panel = client.get(f"/model_builder/open-edit-object-panel/{pattern.id}/").content.decode()
            opened = HourlyEditorInputs(panel).values
            prefix = f"{kind}_{attribute}__"
            assert as_numbers({name.removeprefix(prefix): value for name, value in opened.items()}) == as_numbers(generated_inputs)

            saved = client.post(f"/model_builder/edit-object/{pattern.id}/", {f"{kind}_name": pattern.name, **opened})

            assert saved.status_code == 200
            kept = next(p for p in library_system(client).usage_patterns + library_system(client).edge_usage_patterns
                        if p.id == pattern.id)
            assert as_numbers(getattr(kept, attribute).form_inputs) == as_numbers(generated_inputs)
        assert managers.hourly_occurrences.form_inputs["start_date"] == "2024-12-01"  # the buildings' start, 25 months before 2027

    @titled("ai-bootstrap-edge#edge-builder: a server receives a device's calls once per device deployed, grouped or "
            "fleet total [calls-scale-with-devices]")
    def test_server_calls_scale_with_deployed_devices(self, client, provider):
        generate_web_edge(client, provider, EDGE_ANSWER)
        system = library_system(client)
        germany = next(pattern for pattern in system.edge_usage_patterns if pattern.name == "Stations in Germany")
        heartbeat = next(need for need in server_needs(germany) if "heartbeat" in need.name)
        stations = at_web_year_start(germany.nb_deployments_in_parallel)
        assert at_web_year_start(heartbeat.hourly_volume_per_usage_pattern[germany]) == pytest.approx(12 * stations, rel=0.01)

        two_gateways = json.loads(BUILDING_ANSWER)
        two_gateways["edge_device_groups"][0]["device_counts"]["Gateway"] = 2
        generate_web_edge(client, provider, json.dumps(two_gateways))

        [buildings] = library_system(client).edge_usage_patterns
        [upload] = server_needs(buildings)
        equipped = at_web_year_start(buildings.nb_deployments_in_parallel)
        assert equipped == pytest.approx(1500, rel=0.05)
        assert at_web_year_start(upload.hourly_volume_per_usage_pattern[buildings]) == pytest.approx(6 * 2 * equipped, rel=0.01)

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
        assert "Server calls:" not in body and "Deployments:" not in body
        assert not any(class_name.startswith("Edge") for class_name in saved_modeling(client))

    @planned_test("ai-bootstrap-edge#scope-choice: Start with AI after a Web + edge generation opens on Web only "
                  "[web-by-default]")
    def test_start_opens_on_web_only(self, client, provider):
        pass
