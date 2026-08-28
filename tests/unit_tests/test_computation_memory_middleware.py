import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

from django.http import HttpResponse
from django.test import Client, RequestFactory, override_settings
from django.urls import path
import pytest

from efootprint.api_utils.system_to_json import system_to_json
from efootprint.constants.countries import Countries
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from e_footprint_interface import runtime_memory
from e_footprint_interface import computation_memory_middleware as middleware_module
from model_builder.adapters.repositories import InMemorySystemRepository
from model_builder.domain.entities.web_core.model_web import ModelWeb
from tests.fixtures.system_builders import create_hourly_usage


def _snapshot(working_set_mb=100, *, current_mb=120, inactive_mb=20, rss_mb=80, capacity_mb=4096):
    return runtime_memory.MemorySnapshot(
        rss_bytes=rss_mb * runtime_memory.MIB,
        cgroup_current_bytes=current_mb * runtime_memory.MIB,
        inactive_file_bytes=inactive_mb * runtime_memory.MIB,
        working_set_bytes=working_set_mb * runtime_memory.MIB,
        capacity_bytes=capacity_mb * runtime_memory.MIB,
    )


def _records(log):
    return [
        json.loads(call.args[1])
        for call in log.info.call_args_list
        if len(call.args) > 1 and call.args[0] == "computation_memory %s"
    ]


def _fail_view(request):
    raise RuntimeError("boom")


urlpatterns = [path("model_builder/fail/", _fail_view)]


def _patch_memory(monkeypatch, *, working_set_mb=100):
    snapshot = _snapshot(working_set_mb)
    full_reader = MagicMock(return_value=snapshot)
    lightweight_reader = MagicMock(return_value=snapshot.working_set_bytes)
    monkeypatch.setattr(runtime_memory, "read_memory_snapshot", full_reader)
    monkeypatch.setattr(runtime_memory, "read_cgroup_working_set_bytes", lightweight_reader)
    return full_reader, lightweight_reader


def test_middleware_does_no_monitoring_for_unrelated_routes(monkeypatch):
    get_response = MagicMock(return_value=HttpResponse("ok"))
    observe = MagicMock()
    monkeypatch.setattr(middleware_module, "observe_computations", observe)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_GUARD_MODE", "observe")

    response = middleware_module.ComputationMemoryMiddleware(get_response)(RequestFactory().get("/design/"))

    assert response.status_code == 200
    observe.assert_not_called()


def test_off_mode_is_inert_for_model_builder_requests(monkeypatch):
    get_response = MagicMock(return_value=HttpResponse("ok"))
    observe = MagicMock()
    monkeypatch.setattr(middleware_module, "observe_computations", observe)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_GUARD_MODE", "off")

    middleware_module.ComputationMemoryMiddleware(get_response)(RequestFactory().get("/model_builder/"))

    observe.assert_not_called()


def test_route_uses_url_pattern_instead_of_user_supplied_path_values():
    request = RequestFactory().get("/model_builder/open-edit-object-panel/user-authored-label/")

    assert middleware_module._safe_route(request) == "model_builder/open-edit-object-panel/<object_id>/"


def test_observe_mode_scopes_callback_before_handler_and_restores_on_error(monkeypatch):
    lifecycle = []

    @contextmanager
    def observer_scope(callback):
        lifecycle.append("entered")
        try:
            yield
        finally:
            lifecycle.append("exited")

    def fail(request):
        lifecycle.append("handler")
        raise RuntimeError("boom")

    monitor = MagicMock()
    monitor.request_id = "request-1"
    monkeypatch.setattr(middleware_module, "observe_computations", observer_scope)
    monkeypatch.setattr(middleware_module, "ComputationMemoryMonitor", MagicMock(return_value=monitor))
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_GUARD_MODE", "observe")
    request = RequestFactory().get("/model_builder/")

    with pytest.raises(RuntimeError, match="boom"):
        middleware_module.ComputationMemoryMiddleware(fail)(request)

    assert lifecycle == ["entered", "handler", "exited"]
    monitor.finish.assert_called_once_with("abort")
    assert request.META["efootprint.memory_request_id"] == "request-1"


def test_monitor_samples_every_sixteen_callbacks_away_from_limit(monkeypatch):
    full_reader, lightweight_reader = _patch_memory(monkeypatch)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_LIMIT_BYTES", 4000 * runtime_memory.MIB)
    monitor = middleware_module.ComputationMemoryMonitor(route="model_builder/", method="GET", log=MagicMock())

    for _ in range(15):
        monitor(SimpleNamespace(diagnostic_name="footprint"))
    assert full_reader.call_count == 1
    lightweight_reader.assert_not_called()

    monitor(SimpleNamespace(diagnostic_name="footprint"))
    assert full_reader.call_count == 1
    assert lightweight_reader.call_count == 1
    assert monitor.completed_slots == 16


def test_enforce_mode_keeps_lightweight_per_callback_sampling_near_limit_without_raising(monkeypatch):
    full_reader, lightweight_reader = _patch_memory(monkeypatch, working_set_mb=3800)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_LIMIT_BYTES", 3900 * runtime_memory.MIB)
    monitor = middleware_module.ComputationMemoryMonitor(
        route="model_builder/sankey-diagram/", method="GET", mode="enforce", log=MagicMock()
    )

    for _ in range(3):
        monitor(SimpleNamespace(diagnostic_name="impact_repartition_rows"))

    assert full_reader.call_count == 1
    assert lightweight_reader.call_count == 3
    assert monitor.completed_slots == 3


def test_observe_mode_emits_one_would_abort_then_returns_to_ordinary_cadence(monkeypatch):
    full_reader = MagicMock(side_effect=[_snapshot(3800), _snapshot(3910)])
    lightweight_reader = MagicMock(side_effect=[3910 * runtime_memory.MIB, 3900 * runtime_memory.MIB])
    monkeypatch.setattr(runtime_memory, "read_memory_snapshot", full_reader)
    monkeypatch.setattr(runtime_memory, "read_cgroup_working_set_bytes", lightweight_reader)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_LIMIT_BYTES", 3900 * runtime_memory.MIB)
    log = MagicMock()
    monitor = middleware_module.ComputationMemoryMonitor(route="model_builder/results/", method="GET", log=log)

    for _ in range(16):
        monitor(SimpleNamespace(diagnostic_name="ordinary_slot"))

    assert [record["event"] for record in _records(log)].count("would_abort") == 1
    assert lightweight_reader.call_count == 2
    assert full_reader.call_count == 2


def test_progress_logs_only_new_high_water_bands_and_large_jump_identity(monkeypatch):
    full_reader = MagicMock(
        side_effect=[
            _snapshot(100),
            _snapshot(230),
            _snapshot(400),
        ]
    )
    lightweight_reader = MagicMock(
        side_effect=[120 * runtime_memory.MIB, 230 * runtime_memory.MIB, 400 * runtime_memory.MIB]
    )
    monkeypatch.setattr(runtime_memory, "read_memory_snapshot", full_reader)
    monkeypatch.setattr(runtime_memory, "read_cgroup_working_set_bytes", lightweight_reader)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_LIMIT_BYTES", 200 * runtime_memory.MIB)
    log = MagicMock()
    monitor = middleware_module.ComputationMemoryMonitor(
        route="model_builder/results/", method="GET", mode="enforce", log=log
    )
    monitor(SimpleNamespace(diagnostic_name="ordinary_slot"))
    monitor(SimpleNamespace(diagnostic_name="another_slot"))
    monitor(SimpleNamespace(diagnostic_name="impact_repartition_rows"))

    records = _records(log)
    progress = [record for record in records if record["event"] == "progress"]
    assert len(progress) == 2
    assert "slot" not in progress[0]
    assert progress[1]["slot"] == "impact_repartition_rows"
    assert lightweight_reader.call_count == 3
    assert full_reader.call_count == 3


def test_completion_record_is_correlated_privacy_safe_and_reports_overhead(monkeypatch):
    _patch_memory(monkeypatch)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_LIMIT_BYTES", 4000 * runtime_memory.MIB)
    log = MagicMock()
    monitor = middleware_module.ComputationMemoryMonitor(
        route="model_builder/sankey-diagram/",
        method="POST",
        log=log,
        usage_pattern_count=5,
        modeled_hours=43800,
        attribution_request=True,
    )
    monitor(SimpleNamespace(diagnostic_name="System.impact_repartition_matrix"))
    monitor.finish("complete")

    records = _records(log)
    assert {record["request_id"] for record in records} == {monitor.request_id}
    completion = records[-1]
    assert completion["attribution_matrix_cached"] is False
    assert completion["usage_pattern_count"] == 5
    assert completion["modeled_hours"] == 43800
    assert completion["callback_wall_ms"] >= 0
    assert completion["memory_read_ms"] >= 0
    assert completion["logging_ms"] >= 0
    serialized = json.dumps(completion)
    assert "model_name" not in serialized
    assert "value" not in serialized


@pytest.mark.parametrize(
    ("computed_slot", "status", "expected"),
    [
        (None, "complete", True),
        ("Server.impact_repartition_rows", "complete", False),
        ("System.impact_repartition_matrix", "abort", False),
        (None, "abort", None),
    ],
)
def test_sankey_attribution_state_distinguishes_warm_cold_and_unknown(monkeypatch, computed_slot, status, expected):
    _patch_memory(monkeypatch)
    monitor = middleware_module.ComputationMemoryMonitor(
        route="model_builder/sankey-diagram/", method="GET", log=MagicMock(), attribution_request=True
    )

    if computed_slot is not None:
        monitor(SimpleNamespace(diagnostic_name=computed_slot))
    monitor.finish(status)

    assert monitor.attribution_matrix_cached is expected


def test_middleware_populates_topology_after_real_model_hydration(monkeypatch, minimal_system_data):
    _patch_memory(monkeypatch)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_GUARD_MODE", "observe")
    log = MagicMock()
    monkeypatch.setattr(middleware_module.logger, "info", log.info)

    def hydrate(request):
        ModelWeb(InMemorySystemRepository(), minimal_system_data)
        return HttpResponse("ok")

    request = RequestFactory().get("/model_builder/")
    middleware_module.ComputationMemoryMiddleware(hydrate)(request)

    completion = _records(log)[-1]
    assert completion["usage_pattern_count"] == 1
    assert completion["modeled_hours"] == 8760


def test_middleware_populates_topology_after_real_edge_model_hydration(monkeypatch):
    _patch_memory(monkeypatch)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_GUARD_MODE", "observe")
    log = MagicMock()
    monkeypatch.setattr(middleware_module.logger, "info", log.info)
    edge_pattern = EdgeUsagePattern(
        "Edge pattern",
        edge_usage_journey=EdgeUsageJourney.from_defaults("Edge journey", edge_functions=[]),
        network=Network.wifi_network(),
        country=Countries.FRANCE(),
        hourly_edge_usage_journey_starts=create_hourly_usage(),
    )
    system_data = system_to_json(System("Edge system", usage_patterns=[], edge_usage_patterns=[edge_pattern]))

    def hydrate(request):
        ModelWeb(InMemorySystemRepository(), system_data)
        return HttpResponse("ok")

    response = middleware_module.ComputationMemoryMiddleware(hydrate)(RequestFactory().get("/model_builder/"))

    assert response.status_code == 200
    completion = _records(log)[-1]
    assert completion["usage_pattern_count"] == 1
    assert completion["modeled_hours"] == 8760


def test_model_hydration_keeps_hours_unavailable_for_invalid_edge_duration(monkeypatch):
    _patch_memory(monkeypatch)
    monitor = middleware_module.ComputationMemoryMonitor(route="model_builder/", method="GET", log=MagicMock())
    invalid_hourly_values = SimpleNamespace(
        form_inputs={"modeling_duration_value": 1, "modeling_duration_unit": "unsupported"}
    )
    model_web = SimpleNamespace(
        usage_patterns=[],
        edge_usage_patterns=[
            SimpleNamespace(modeling_obj=SimpleNamespace(hourly_edge_usage_journey_starts=invalid_hourly_values))
        ],
    )

    monitor.model_hydrated(model_web)

    assert monitor.usage_pattern_count == 1
    assert monitor.modeled_hours is None


def test_middleware_keeps_topology_unavailable_when_no_model_was_hydrated(monkeypatch):
    _patch_memory(monkeypatch)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_GUARD_MODE", "observe")
    log = MagicMock()
    middleware = middleware_module.ComputationMemoryMiddleware(lambda request: HttpResponse("ok"))
    monkeypatch.setattr(middleware_module.logger, "info", log.info)

    middleware(RequestFactory().get("/model_builder/"))

    completion = _records(log)[-1]
    assert completion["usage_pattern_count"] is None
    assert completion["modeled_hours"] is None


@override_settings(
    ROOT_URLCONF=__name__,
    MIDDLEWARE=["e_footprint_interface.computation_memory_middleware.ComputationMemoryMiddleware"],
    DEBUG_PROPAGATE_EXCEPTIONS=False,
)
def test_real_django_middleware_chain_reports_view_exception_as_abort(monkeypatch):
    _patch_memory(monkeypatch)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_GUARD_MODE", "observe")
    log = MagicMock()
    monkeypatch.setattr(middleware_module.logger, "info", log.info)

    response = Client(raise_request_exception=False).get("/model_builder/fail/")

    assert response.status_code == 500
    records = _records(log)
    assert [record["event"] for record in records] == ["start", "abort"]
    assert records[-1]["usage_pattern_count"] is None
    assert records[-1]["modeled_hours"] is None
