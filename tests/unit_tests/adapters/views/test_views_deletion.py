import pytest
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.builders.usage.edge.recurrent_edge_workload import RecurrentEdgeWorkload
from efootprint.constants.countries import Countries
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

from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.domain.entities.web_core.model_web import ModelWeb
from tests.fixtures.system_builders import create_hourly_usage


@pytest.fixture
def edge_system_data():
    """One edge function whose two recurrent edge processes and recurrent server need share one edge computer, plus a
    recurrent edge workload on an edge appliance."""
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
    return system_to_json(
        System("Edge system", usage_patterns=[], edge_usage_patterns=[edge_usage_pattern]), save_computed_state=False)


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


@pytest.mark.xfail(strict=True, reason="bug-fixes-2026-10 Task 8")
@pytest.mark.django_db
@pytest.mark.parametrize("class_name,device_class_name,device_name", [
    ("EdgeComputerCPUComponent", "EdgeComputer", "Shared edge computer"),
    ("EdgeComputerRAMComponent", "EdgeComputer", "Shared edge computer"),
    ("EdgeStorage", "EdgeComputer", "Shared edge computer"),
    ("EdgeApplianceComponent", "EdgeAppliance", "Edge appliance")])
def test_library_built_edge_component_deletion_is_blocked_and_edits_rerender_its_device(
        client, monkeypatch, edge_system_data, class_name, device_class_name, device_name):
    monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
    repository = SessionSystemRepository(client.session)
    repository.save_data(edge_system_data)
    object_id = next(iter(edge_system_data[class_name]))
    device_id = _id_by_name(edge_system_data, device_class_name, device_name)
    device_web_id = ModelWeb(repository).get_web_object_from_efootprint_id(device_id).web_id

    confirmation = client.get(f"/model_builder/ask-delete-object/{object_id}/").content.decode()
    assert "is referenced by" in confirmation
    assert device_name in confirmation
    assert "Yes, delete" not in confirmation

    deletion = client.post(f"/model_builder/delete-object/{object_id}/")
    saved_after = SessionSystemRepository(client.session).get_system_data()
    assert deletion.status_code != 200
    assert object_id in saved_after[class_name]
    assert object_id in saved_after[device_class_name][device_id]["components"]

    edition = client.post(f"/model_builder/edit-object/{object_id}/", {f"{class_name}_name": "Renamed component"})
    assert edition.status_code == 200
    assert f"hx-swap-oob='outerHTML:#{device_web_id}'" in edition.content.decode()
