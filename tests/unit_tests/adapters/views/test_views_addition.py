import json
import re
from unittest.mock import MagicMock

import pytest
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.timeseries import WeeklyPatternValidationError
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.constants.countries import Countries
from efootprint.core.hardware.edge.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed

from comprehension_harness.python.declare import reproduces
from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.domain.entities.web_core.model_web import ModelWeb
from tests.fixtures.system_builders import create_hourly_usage


def _edge_system_with_recurrent_parents() -> System:
    edge_computer = EdgeComputer.from_defaults("Edge computer", storage=EdgeStorage.from_defaults("Edge storage"))
    edge_device = EdgeDevice.from_defaults("Edge device", components=[EdgeCPUComponent.from_defaults("CPU")])
    edge_function = EdgeFunction(
        "Edge function",
        recurrent_edge_device_needs=[
            RecurrentEdgeProcess.from_defaults("Edge process", edge_device=edge_computer),
            RecurrentEdgeDeviceNeed("Device need", edge_device=edge_device, recurrent_edge_component_needs=[]),
        ],
        recurrent_server_needs=[],
    )
    edge_usage_pattern = EdgeUsagePattern(
        "Edge usage pattern",
        edge_usage_journeys=[EdgeUsageJourney.from_defaults("Edge journey", edge_functions=[edge_function])],
        network=Network.wifi_network(),
        country=Countries.FRANCE(),
        hourly_deployment_starts=create_hourly_usage(),
    )

    return System("System", usage_patterns=[], edge_usage_patterns=[edge_usage_pattern])


def _input_tag(body: str, name: str) -> str:
    marker = f'name="{name}"'
    start = body.rfind("<input", 0, body.index(marker))
    return body[start:body.index(">", start) + 1]


@pytest.mark.django_db
def test_weekly_library_validation_error_uses_standard_modal_without_mutating_session(
    client, minimal_system_data, monkeypatch
):
    repository = SessionSystemRepository(client.session)
    repository.save_data(minimal_system_data)
    saved_before = repository.get_system_data()
    execute = MagicMock(
        side_effect=WeeklyPatternValidationError(
            [
                {
                    "path": "profiles",
                    "code": "missing_day_assignment",
                    "message": "Day 1 must be assigned to exactly one profile.",
                }
            ]
        )
    )
    monkeypatch.setattr("model_builder.adapters.views.views_addition.CreateObjectUseCase.execute", execute)
    invalid_pattern = {
        "unit": "cpu_core",
        "profiles": [{"name": "incomplete", "days": [0], "baseline": 1, "ranges": []}],
    }

    response = client.post(
        "/model_builder/add-object/RecurrentEdgeProcess/",
        {
            "type_object_available": "RecurrentEdgeProcess",
            "RecurrentEdgeProcess_name": "Invalid process",
            "RecurrentEdgeProcess_recurrent_compute_needed__weekly_pattern": json.dumps(invalid_pattern),
        },
    )

    assert response.status_code == 422
    assert response.headers["HX-Reswap"] == "none"
    assert "Day 1 must be assigned to exactly one profile" in response.content.decode()
    execute.assert_called_once()
    assert SessionSystemRepository(client.session).get_system_data() == saved_before


@pytest.mark.django_db
@pytest.mark.parametrize("error,status", [(ValueError("Unexpected failure"), 500), (RuntimeError("Failure"), 500)])
def test_unclassified_creation_failure_uses_server_error_modal(client, minimal_system_data, monkeypatch, error, status):
    monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
    SessionSystemRepository(client.session).save_data(minimal_system_data)
    monkeypatch.setattr("model_builder.adapters.views.views_addition.CreateObjectUseCase.execute",
                        MagicMock(side_effect=error))
    response = client.post("/model_builder/add-object/Server/", {"type_object_available": "Server"})
    assert response.status_code == status
    assert response["HX-Reswap"] == "none"
    assert 'id="modal-container" hx-swap-oob="true"' in response.content.decode()


@pytest.mark.django_db
def test_creation_form_parsing_failure_uses_validation_modal(client, minimal_system_data, monkeypatch):
    monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
    SessionSystemRepository(client.session).save_data(minimal_system_data)
    execute = MagicMock()
    monkeypatch.setattr("model_builder.adapters.views.views_addition.CreateObjectUseCase.execute", execute)
    response = client.post("/model_builder/add-object/Server/", {
        "type_object_available": "Server", "Server_lifespan": "invalid", "Server_lifespan__unit": "year"})
    assert response.status_code == 422
    assert response["HX-Reswap"] == "none"
    execute.assert_not_called()


@reproduces("bug-fixes-2026-10#recurrent-unit-each-hour: a recurrent constant editor reads per hour in its unit box "
            "and its helper, and posts the unit alone")
@pytest.mark.django_db
def test_recurrent_constant_editor_reads_as_a_per_hour_value(client):
    SessionSystemRepository(client.session).save_data(
        system_to_json(_edge_system_with_recurrent_parents(), save_computed_state=False))
    parent = ModelWeb(SessionSystemRepository(client.session)).get_efootprint_objects_from_efootprint_type(
        "RecurrentEdgeDeviceNeed")[0]
    panels = {"RecurrentServerNeed": "", "RecurrentEdgeProcess": "",
              "RecurrentEdgeComponentNeed": f"?efootprint_id_of_parent_to_link_to={parent.id}"}
    units = {
        "RecurrentServerNeed_recurrent_volume_per_edge_device": "occurrence",
        "RecurrentEdgeProcess_recurrent_compute_needed": "cpu_core",
        "RecurrentEdgeProcess_recurrent_ram_needed": "GB_ram",
        "RecurrentEdgeProcess_recurrent_storage_needed": "GB_stored",
        "RecurrentEdgeWorkload_recurrent_workload": "concurrent",
        "RecurrentEdgeComponentNeed_recurrent_need": "concurrent",
    }

    box_reads, posted, helpers = [], {}, set()
    for object_type, query in panels.items():
        body = client.get(f"/model_builder/open-create-object-panel/{object_type}/{query}").content.decode()
        for field_web_id in re.findall(r'name="([^"]*)__constant_unit"', body):
            unit_input = _input_tag(body, f"{field_web_id}__constant_unit")
            posted[field_web_id] = re.search(r'value="([^"]*)"', unit_input).group(1)
            helper_marker = f'id="{field_web_id}__constant_value_help"'
            unit_box_html = body[body.index(unit_input):body.rfind("<small", 0, body.index(helper_marker))]
            box_reads.append(" ".join(
                re.sub(r"<[^>]*>", " ", unit_box_html.replace(unit_input, posted[field_web_id])).split()))
            helper_start = body.index(">", body.index(helper_marker)) + 1
            helpers.add(" ".join(body[helper_start:body.index("</small>", helper_start)].split()))
    seen = {"what the unit boxes read": sorted(box_reads), "what the helpers say": sorted(helpers),
            "the unit each editor posts": posted}

    assert seen == {
        "what the unit boxes read": sorted(f"{unit} each hour" for unit in units.values()),
        "what the helpers say": ["All hours of the canonical week (168 hours) will use this value."],
        "the unit each editor posts": units,
    }
