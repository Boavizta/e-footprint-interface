import pytest
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.external_apis.ecologits.ecologits_external_api import (
    EcoLogitsGenAIExternalAPI, EcoLogitsGenAIExternalAPIJob)
from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.builders.usage.edge.recurrent_edge_workload import RecurrentEdgeWorkload
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern

from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.domain.entities.web_core.model_web import ModelWeb
from tests.fixtures.system_builders import create_hourly_usage


@pytest.fixture
def edge_system_data():
    """Edge needs, components, and an external API server, all built through their owning objects."""
    edge_computer = EdgeComputer.from_defaults("Shared edge computer", storage=EdgeStorage.from_defaults("Edge storage"))
    server = Server.from_defaults("Server", storage=Storage.from_defaults("Server storage"))
    edge_function = EdgeFunction(
        "Edge function",
        recurrent_edge_device_needs=[
            RecurrentEdgeProcess.from_defaults("Edge process", edge_device=edge_computer),
            RecurrentEdgeProcess.from_defaults("Sibling edge process", edge_device=edge_computer),
            RecurrentEdgeWorkload.from_defaults("Edge workload", edge_device=EdgeAppliance.from_defaults("Edge appliance"))],
        recurrent_server_needs=[RecurrentServerNeed.from_defaults(
            "Server need", edge_device=edge_computer, jobs=[Job.from_defaults("Upload job", server=server)])])
    edge_usage_pattern = EdgeUsagePattern(
        "Edge usage pattern",
        edge_usage_journeys=[EdgeUsageJourney.from_defaults("Edge usage journey", edge_functions=[edge_function])],
        network=Network.wifi_network(), country=Countries.FRANCE(), hourly_deployment_starts=create_hourly_usage())
    external_api = EcoLogitsGenAIExternalAPI.from_defaults("LLM API")
    usage_pattern = UsagePattern(
        "API usage pattern",
        usage_journeys={UsageJourney("API journey", uj_steps=[UsageJourneyStep.from_defaults(
            "API step", jobs=[EcoLogitsGenAIExternalAPIJob.from_defaults("API job", external_api=external_api)])]):
            SourceValue(1 * u.dimensionless)},
        devices=[Device.from_defaults("API device")],
        network=Network.from_defaults("API network"),
        country=Countries.FRANCE(),
        hourly_occurrences=create_hourly_usage(),
    )
    return system_to_json(
        System("Edge system", usage_patterns=[usage_pattern], edge_usage_patterns=[edge_usage_pattern]),
        save_computed_state=False)


def _id_by_name(system_data: dict, class_name: str, name: str) -> str:
    return next(object_id for object_id, obj in system_data[class_name].items() if obj["name"] == name)


@pytest.mark.django_db
def test_object_deletion_requires_post_and_confirmation_uses_it(client, minimal_system_data):
    repository = SessionSystemRepository(client.session)
    repository.save_data(minimal_system_data)
    object_id = next(iter(minimal_system_data["UsagePattern"]))
    url = f"/model_builder/delete-object/{object_id}/"
    saved_before = repository.get_system_data()

    confirmation = client.get(f"/model_builder/ask-delete-object/{object_id}/")
    assert f'hx-post="{url}"' in confirmation.content.decode()
    assert 'hx-target="#modal-container"' in confirmation.content.decode()
    assert 'hx-swap="none"' in confirmation.content.decode()
    assert client.get(url).status_code == 405
    assert repository.get_system_data() == saved_before

    response = client.post(url)
    assert response.status_code == 200
    assert "openModalDialog" not in response.headers.get("HX-Trigger-After-Settle", "")
    assert object_id not in SessionSystemRepository(client.session).get_system_data().get("UsagePattern", {})


@pytest.mark.django_db
@pytest.mark.parametrize("class_name,name", [("RecurrentServerNeed", "Server need"),
                                             ("RecurrentEdgeProcess", "Edge process")])
def test_recurrent_need_deletion_rerenders_its_edge_usage_journey_card(client, edge_system_data, class_name, name):
    repository = SessionSystemRepository(client.session)
    repository.save_data(edge_system_data)
    object_id = _id_by_name(edge_system_data, class_name, name)
    sibling_id = _id_by_name(edge_system_data, "RecurrentEdgeProcess", "Sibling edge process")
    journey_id = _id_by_name(edge_system_data, "EdgeUsageJourney", "Edge usage journey")
    journey_web_id = ModelWeb(repository).get_web_object_from_efootprint_id(journey_id).web_id

    response = client.post(f"/model_builder/delete-object/{object_id}/")

    body = response.content.decode()
    assert response.status_code == 200
    assert "openModalDialog" not in response.headers.get("HX-Trigger-After-Settle", "")
    assert f"hx-swap-oob='outerHTML:#{journey_web_id}'" in body
    assert object_id not in body
    assert sibling_id in body
    assert object_id not in SessionSystemRepository(client.session).get_system_data().get(class_name, {})


@pytest.mark.django_db
@pytest.mark.parametrize("class_name,parent_name", [
    ("EdgeComputerCPUComponent", "Shared edge computer"),
    ("EdgeComputerRAMComponent", "Shared edge computer"),
    ("EdgeApplianceComponent", "Edge appliance"),
    ("RecurrentEdgeProcessCPUNeed", "Edge process"),
    ("RecurrentEdgeWorkloadNeed", "Edge workload"),
    ("EcoLogitsGenAIExternalAPIServer", "LLM API"),
])
def test_internally_managed_objects_reject_standalone_edits_and_deletion(
        client, monkeypatch, edge_system_data, class_name, parent_name):
    monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
    repository = SessionSystemRepository(client.session)
    repository.save_data(edge_system_data)
    object_names = {
        "EdgeComputerCPUComponent": "Shared edge computer CPU",
        "EdgeComputerRAMComponent": "Shared edge computer RAM",
        "EdgeApplianceComponent": "Edge appliance appliance",
        "RecurrentEdgeProcessCPUNeed": "Edge process CPU need",
        "RecurrentEdgeWorkloadNeed": "Edge workload workload need",
        "EcoLogitsGenAIExternalAPIServer": "LLM API server",
    }
    object_id = _id_by_name(edge_system_data, class_name, object_names[class_name])
    saved_before = repository.get_system_data()

    confirmation = client.get(f"/model_builder/ask-delete-object/{object_id}/").content.decode()
    assert parent_name in confirmation
    assert "Yes, delete" not in confirmation

    deletion = client.post(f"/model_builder/delete-object/{object_id}/")
    assert deletion.status_code != 200
    assert 'id="exception-msg"' in deletion.content.decode()
    assert parent_name in deletion.content.decode()

    edition = client.post(f"/model_builder/edit-object/{object_id}/", {f"{class_name}_name": "Renamed object"})
    assert edition.status_code != 200
    assert 'id="exception-msg"' in edition.content.decode()
    assert parent_name in edition.content.decode()
    assert SessionSystemRepository(client.session).get_system_data() == saved_before
