"""View-layer smoke tests for the results endpoints.

Catches "Results view returns 500 on a freshly-built minimal model" — the
failure mode where a real attribution path explodes on a shape no fixture
exercised end-to-end. Library-side bugs are covered by efootprint's
run_test_materialize_all_cached_properties; these tests defend the interface
seam (session repository, view parameter shapes, ModelWeb rebuild,
SystemValidationService) on each archetype.

Each archetype × endpoint pair is one test. Endpoints covered:
- GET /model_builder/result-chart/    — fires the moment "Results" is clicked
- POST /model_builder/sankey-diagram/ — fires when the panel settles

RAISE_EXCEPTIONS=1 is critical: without it, render_exception_modal_if_error
absorbs view exceptions into a modal returned with status 200, and a status-code
assertion would silently pass.
"""

from copy import deepcopy
from datetime import datetime

import numpy as np
import pytest
from pint import Quantity
from efootprint.abstract_modeling_classes.reactive_core import observe_computations
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceRecurrentValues
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.edge.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
from efootprint.core.hardware.edge.edge_ram_component import EdgeRAMComponent
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern

from e_footprint_interface import computation_memory_middleware, runtime_memory
from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.views.sankey_views import DEFAULT_ACTIVE_COLUMNS
from model_builder.domain.entities.web_core.model_web import ModelWeb
from tests.fixtures.system_builders import create_hourly_usage


START_DATE = datetime(2025, 1, 1)
_EUP_HOURS = [1000] * 9


def _build_basic_web() -> System:
    storage = Storage.from_defaults("Web Storage")
    server = Server.from_defaults("Web Server", storage=storage)
    job = Job.from_defaults("Web Job", server=server)
    step = UsageJourneyStep.from_defaults("Web Step", jobs=[job])
    journey = UsageJourney("Web Journey", uj_steps=[step])
    alternate_journey = UsageJourney("Alternate Web Journey", uj_steps=[step])
    up = UsagePattern(
        "Web UP",
        usage_journeys={
            journey: SourceValue(1 * u.dimensionless),
            alternate_journey: SourceValue(0.25 * u.dimensionless),
        },
        devices=[Device.from_defaults("Web Device")],
        network=Network.from_defaults("Web Network"),
        country=Countries.FRANCE(),
        hourly_occurrences=create_hourly_usage(),
    )
    shared_journey_up = UsagePattern(
        "Shared Journey UP",
        usage_journeys={journey: SourceValue(0.5 * u.dimensionless)},
        devices=[Device.from_defaults("Shared Web Device")],
        network=up.network,
        country=up.country,
        hourly_occurrences=create_hourly_usage(),
    )
    return System("Smoke Basic Web", usage_patterns=[up, shared_journey_up], edge_usage_patterns=[])


def _build_basic_edge_no_server() -> System:
    storage = EdgeStorage.from_defaults("Edge Storage", base_storage_need=SourceValue(100 * u.GB_stored))
    computer = EdgeComputer.from_defaults(
        "Edge Computer", storage=storage, base_compute_consumption=SourceValue(0.1 * u.cpu_core)
    )
    process = RecurrentEdgeProcess.from_defaults("Edge Process", edge_device=computer)
    function = EdgeFunction("Edge Function", recurrent_edge_device_needs=[process], recurrent_server_needs=[])
    journey = EdgeUsageJourney.from_defaults("Edge UJ", edge_functions=[function])
    alternate_journey = EdgeUsageJourney.from_defaults("Alternate Edge UJ", edge_functions=[function])
    eup = EdgeUsagePattern(
        "Edge UP",
        edge_usage_journeys=[journey, alternate_journey],
        network=Network.wifi_network(),
        country=Countries.FRANCE(),
        hourly_deployment_starts=create_source_hourly_values_from_list(_EUP_HOURS, START_DATE),
    )
    return System("Smoke Basic Edge No Server", usage_patterns=[], edge_usage_patterns=[eup])


def _build_edge_with_server_need() -> System:
    server_storage = Storage.from_defaults("Server Storage")
    server = Server.from_defaults("Edge Server", storage=server_storage)
    server_job = Job.from_defaults("Server Job", server=server)

    edge_storage = EdgeStorage.from_defaults("Edge Storage", base_storage_need=SourceValue(100 * u.GB_stored))
    computer = EdgeComputer.from_defaults(
        "Edge Computer", storage=edge_storage, base_compute_consumption=SourceValue(0.1 * u.cpu_core)
    )
    process = RecurrentEdgeProcess.from_defaults("Edge Process", edge_device=computer)
    server_need = RecurrentServerNeed(
        "Server Need",
        edge_device=computer,
        recurrent_volume_per_edge_device=SourceRecurrentValues(
            Quantity(np.array([1] * 168, dtype=np.float32), u.occurrence)
        ),
        jobs=[server_job],
    )
    function = EdgeFunction(
        "Edge Function",
        recurrent_edge_device_needs=[process],
        recurrent_server_needs=[server_need],
    )
    journey = EdgeUsageJourney.from_defaults("Edge UJ", edge_functions=[function])
    eup = EdgeUsagePattern(
        "Edge UP",
        edge_usage_journeys=[journey],
        network=Network.wifi_network(),
        country=Countries.FRANCE(),
        hourly_deployment_starts=create_source_hourly_values_from_list(_EUP_HOURS, START_DATE),
    )
    return System("Smoke Edge With Server", usage_patterns=[], edge_usage_patterns=[eup])


def _build_edge_device_group() -> System:
    ram = EdgeRAMComponent.from_defaults("RAM")
    cpu = EdgeCPUComponent.from_defaults("CPU")
    device = EdgeDevice.from_defaults("Grouped Device", components=[ram, cpu])

    ram_need = RecurrentEdgeComponentNeed(
        "RAM need",
        edge_component=ram,
        recurrent_need=SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.GB_ram)),
    )
    cpu_need = RecurrentEdgeComponentNeed(
        "CPU need",
        edge_component=cpu,
        recurrent_need=SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)),
    )
    device_need = RecurrentEdgeDeviceNeed(
        "Device Need", edge_device=device, recurrent_edge_component_needs=[ram_need, cpu_need]
    )
    function = EdgeFunction("Edge Function", recurrent_edge_device_needs=[device_need], recurrent_server_needs=[])
    journey = EdgeUsageJourney.from_defaults("Edge UJ", edge_functions=[function])
    eup = EdgeUsagePattern(
        "Edge UP",
        edge_usage_journeys=[journey],
        network=Network.wifi_network(),
        country=Countries.FRANCE(),
        hourly_deployment_starts=create_source_hourly_values_from_list(_EUP_HOURS, START_DATE),
    )

    floor = EdgeDeviceGroup("Floor", sub_group_counts={}, edge_device_counts={device: SourceValue(4 * u.dimensionless)})
    EdgeDeviceGroup(
        "Building",
        sub_group_counts={floor: SourceValue(3 * u.dimensionless)},
        edge_device_counts={},
    )
    return System("Smoke Edge Device Group", usage_patterns=[], edge_usage_patterns=[eup])


ARCHETYPES = [
    ("basic_web", _build_basic_web),
    ("basic_edge_no_server", _build_basic_edge_no_server),
    ("edge_with_server_need", _build_edge_with_server_need),
    ("edge_device_group", _build_edge_device_group),
]


_DEFAULT_POST = {
    "card_id": "1",
    "lifecycle_phase_filter": "",
    "aggregation_threshold_percent": "1.0",
    "active_columns": list(DEFAULT_ACTIVE_COLUMNS),
    "display_column_headers": "on",
    "node_label_max_length": "15",
}


ENDPOINTS = [
    ("result_chart", lambda client: client.get("/model_builder/result-chart/")),
    ("sankey_diagram", lambda client: client.post("/model_builder/sankey-diagram/", _DEFAULT_POST)),
]


@pytest.fixture(autouse=True)
def raise_view_exceptions(monkeypatch):
    monkeypatch.setenv("RAISE_EXCEPTIONS", "1")


@pytest.mark.django_db
@pytest.mark.parametrize("hit", [h for _, h in ENDPOINTS], ids=[name for name, _ in ENDPOINTS])
@pytest.mark.parametrize("builder", [b for _, b in ARCHETYPES], ids=[name for name, _ in ARCHETYPES])
def test_results_endpoint_smoke(client, builder, hit):
    system = builder()
    SessionSystemRepository(client.session).save_data(system_to_json(system, save_computed_state=False))
    assert hit(client).status_code == 200


@pytest.mark.django_db
def test_result_chart_persists_newly_computed_footprints_only_once(client, monkeypatch):
    system = _build_basic_web()
    repository = SessionSystemRepository(client.session)
    repository.save_data(system_to_json(system, save_computed_state=False))
    persist_calls = 0
    original_persist_to_cache = ModelWeb.persist_to_cache

    def count_persist(model_web):
        nonlocal persist_calls
        persist_calls += 1
        return original_persist_to_cache(model_web)

    monkeypatch.setattr(ModelWeb, "persist_to_cache", count_persist)

    def hit_result_chart():
        completed_slots = 0

        def count_completion(_slot):
            nonlocal completed_slots
            completed_slots += 1

        with observe_computations(count_completion):
            response = client.get("/model_builder/result-chart/", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        return completed_slots

    assert hit_result_chart() > 0
    assert persist_calls == 1
    assert "total_footprint" in repository.get_system_data()["System"][system.id]
    assert hit_result_chart() == 0
    assert persist_calls == 1


@pytest.mark.django_db
def test_cold_sankey_memory_trip_uses_real_observer_and_peek_coverage_without_persisting(client, monkeypatch):
    system_data = system_to_json(_build_basic_web(), save_computed_state=False)
    repository = SessionSystemRepository(client.session)
    repository.save_data(system_data)
    persisted_before = deepcopy(repository.get_system_data())
    start_snapshot = runtime_memory.MemorySnapshot(
        rss_bytes=100 * runtime_memory.MIB,
        cgroup_current_bytes=3820 * runtime_memory.MIB,
        inactive_file_bytes=20 * runtime_memory.MIB,
        working_set_bytes=3800 * runtime_memory.MIB,
        capacity_bytes=4096 * runtime_memory.MIB,
    )
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_GUARD_MODE", "enforce")
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_LIMIT_BYTES", 3900 * runtime_memory.MIB)
    monkeypatch.setattr(runtime_memory, "CGROUP_CAPACITY_BYTES", 4096 * runtime_memory.MIB)
    monkeypatch.setattr(runtime_memory, "read_memory_snapshot", lambda _process: start_snapshot)
    monkeypatch.setattr(
        runtime_memory,
        "read_cgroup_working_set_bytes",
        lambda: 3900 * runtime_memory.MIB,
    )

    response = client.post("/model_builder/sankey-diagram/", _DEFAULT_POST)

    content = response.content.decode()
    assert response.status_code == 200
    assert "data-sankey-memory-limit" in content
    assert "completion coverage only" in content
    assert "0%" in content
    assert "modal-container" not in content
    assert SessionSystemRepository(client.session).get_system_data() == persisted_before
