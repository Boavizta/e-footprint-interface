import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

from django.http import HttpResponse
from django.test import Client, RequestFactory, override_settings
from django.urls import path
import pytest

from efootprint.abstract_modeling_classes.reactive_core import observe_computations
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from e_footprint_interface import runtime_memory
from e_footprint_interface import computation_memory_middleware as middleware_module
from model_builder.adapters.repositories import InMemorySystemRepository
from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.views import views
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.exceptions import ComputationMemoryLimitExceeded
from model_builder.domain.model_hydration_observer import report_model_hydrated
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


def _monitor_errors(log):
    return [
        json.loads(call.args[1])
        for call in log.error.call_args_list
        if len(call.args) > 1 and call.args[0] == "computation_memory %s"
    ]


def _fail_view(request):
    raise RuntimeError("boom")


def _ok_view(request):
    return HttpResponse("ok")


def _capacity_fail_view(request):
    raise ComputationMemoryLimitExceeded(
        working_set_bytes=3500 * runtime_memory.MIB,
        limit_bytes=3400 * runtime_memory.MIB,
        capacity_bytes=4096 * runtime_memory.MIB,
    )


def _report_hydrated_view(request):
    report_model_hydrated(SimpleNamespace())
    return HttpResponse("hydrated")


urlpatterns = [
    path("model_builder/fail/", _fail_view),
    path("model_builder/ok/", _ok_view),
    path("model_builder/report-hydrated/", _report_hydrated_view),
    path("model_builder/capacity-fail/", _capacity_fail_view),
    path("model_builder/download-json/", views.download_json),
]


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


def test_enforce_mode_raises_at_threshold_and_latches_for_remaining_callbacks(monkeypatch):
    full_reader, lightweight_reader = _patch_memory(monkeypatch, working_set_mb=3900)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_LIMIT_BYTES", 3900 * runtime_memory.MIB)
    monkeypatch.setattr(runtime_memory, "CGROUP_CAPACITY_BYTES", 4096 * runtime_memory.MIB)
    log = MagicMock()
    monitor = middleware_module.ComputationMemoryMonitor(
        route="model_builder/sankey-diagram/", method="GET", mode="enforce", log=log
    )

    with pytest.raises(ComputationMemoryLimitExceeded) as raised:
        monitor(SimpleNamespace(diagnostic_name="impact_repartition_rows"))
    for _ in range(15):
        monitor(SimpleNamespace(diagnostic_name="rollback_guard"))

    assert raised.value.capacity_bytes == 4096 * runtime_memory.MIB
    assert raised.value.limit_bytes == 3900 * runtime_memory.MIB
    assert [record["event"] for record in _records(log)].count("abort") == 1
    assert full_reader.call_count == 2
    assert lightweight_reader.call_count == 2
    assert monitor.completed_slots == 16


def test_real_monitor_latches_while_modeling_update_rolls_back(monkeypatch):
    start_snapshot = _snapshot(3800, current_mb=3820, inactive_mb=20)
    monkeypatch.setattr(runtime_memory, "read_memory_snapshot", MagicMock(return_value=start_snapshot))
    monkeypatch.setattr(
        runtime_memory,
        "read_cgroup_working_set_bytes",
        MagicMock(return_value=3900 * runtime_memory.MIB),
    )
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_LIMIT_BYTES", 3900 * runtime_memory.MIB)
    monkeypatch.setattr(runtime_memory, "CGROUP_CAPACITY_BYTES", 4096 * runtime_memory.MIB)
    log = MagicMock()
    monitor = middleware_module.ComputationMemoryMonitor(
        route="model_builder/edit-object/<object_id>/", method="POST", mode="enforce", log=log
    )
    boundary = middleware_module._TelemetryBoundary(monitor)
    server = Server.from_defaults("Guarded server", storage=Storage.from_defaults("Guarded storage"))
    original_ram = server.ram
    original_available_ram = server.available_ram_per_instance.value

    with observe_computations(boundary):
        with pytest.raises(ComputationMemoryLimitExceeded):
            ModelingUpdate([[server.ram, SourceValue(256 * u.GB_ram)]])

    assert server.ram is original_ram
    assert server.available_ram_per_instance.value == original_available_ram
    assert monitor.completed_slots >= 2
    assert [record["event"] for record in _records(log)].count("abort") == 1


def test_enforce_mode_does_not_raise_below_threshold_boundary(monkeypatch):
    _patch_memory(monkeypatch, working_set_mb=3899)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_LIMIT_BYTES", 3900 * runtime_memory.MIB)
    monitor = middleware_module.ComputationMemoryMonitor(
        route="model_builder/results/", method="GET", mode="enforce", log=MagicMock()
    )

    monitor(SimpleNamespace(diagnostic_name="ordinary_slot"))

    assert monitor.completed_slots == 1
    assert monitor._limit_exceeded is False


def test_enforce_mode_still_raises_when_abort_diagnostics_fail(monkeypatch):
    _patch_memory(monkeypatch, working_set_mb=3900)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_LIMIT_BYTES", 3900 * runtime_memory.MIB)
    log = MagicMock()

    def fail_abort_record(_message, payload):
        if json.loads(payload)["event"] == "abort":
            raise RuntimeError("logging failed")

    log.info.side_effect = fail_abort_record
    monitor = middleware_module.ComputationMemoryMonitor(
        route="model_builder/results/", method="GET", mode="enforce", log=log
    )

    with pytest.raises(ComputationMemoryLimitExceeded):
        monitor(SimpleNamespace(diagnostic_name="ordinary_slot"))

    assert monitor._limit_exceeded is True
    assert monitor._abort_emitted is False


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
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_LIMIT_BYTES", 2000 * runtime_memory.MIB)
    monkeypatch.setattr(middleware_module, "NEAR_LIMIT_WINDOW_BYTES", 2000 * runtime_memory.MIB)
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


def test_completion_record_is_correlated_privacy_safe_and_omits_temporary_overhead_counters(monkeypatch):
    _patch_memory(monkeypatch)
    resolved_limit = 4000 * runtime_memory.MIB + 123
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_LIMIT_BYTES", resolved_limit)
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
    assert {record["limit_mb"] for record in records} == {resolved_limit / runtime_memory.MIB}
    completion = records[-1]
    assert completion["attribution_matrix_cached"] is False
    assert completion["usage_pattern_count"] == 5
    assert completion["modeled_hours"] == 43800
    assert "callback_wall_ms" not in completion
    assert "max_callback_ms" not in completion
    assert "memory_read_ms" not in completion
    assert "logging_ms" not in completion
    assert monitor.callback_wall_ms == 0
    assert monitor.memory_read_ms == 0
    assert monitor.logging_ms == 0
    serialized = json.dumps(completion)
    assert "model_name" not in serialized
    assert "value" not in serialized


def test_records_report_an_unavailable_resolved_limit_explicitly(monkeypatch):
    _patch_memory(monkeypatch)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_LIMIT_BYTES", None)
    log = MagicMock()
    monitor = middleware_module.ComputationMemoryMonitor(route="model_builder/results/", method="GET", log=log)

    monitor.finish("complete")

    assert {record["limit_mb"] for record in _records(log)} == {None}


def test_local_profiler_can_still_measure_monitor_overhead(monkeypatch):
    _patch_memory(monkeypatch)
    monitor = middleware_module.ComputationMemoryMonitor(route="profile/cold-sankey", method="PROFILE", log=MagicMock())

    monitor(SimpleNamespace(diagnostic_name="ordinary_slot"))
    monitor.finish("complete")

    assert monitor.callback_wall_ms > 0
    assert monitor.memory_read_ms > 0
    assert monitor.logging_ms > 0


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
)
def test_real_middleware_disables_observation_when_hydration_callback_fails(monkeypatch):
    _patch_memory(monkeypatch)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_GUARD_MODE", "observe")
    monkeypatch.setattr(
        middleware_module.ComputationMemoryMonitor,
        "model_hydrated",
        MagicMock(side_effect=AttributeError("user-authored-sensitive-value")),
    )
    log = MagicMock()
    monkeypatch.setattr(middleware_module.logger, "info", log.info)
    monkeypatch.setattr(middleware_module.logger, "error", log.error)

    response = Client().get("/model_builder/report-hydrated/")

    assert response.status_code == 200
    assert response.content == b"hydrated"
    errors = _monitor_errors(log)
    assert len(errors) == 1
    assert errors[0]["phase"] == "model_hydrated"
    assert errors[0]["error_type"] == "AttributeError"
    assert "user-authored-sensitive-value" not in json.dumps(errors[0])


@override_settings(
    ROOT_URLCONF=__name__,
    MIDDLEWARE=["e_footprint_interface.computation_memory_middleware.ComputationMemoryMiddleware"],
)
@pytest.mark.parametrize("mode", ["observe", "enforce"])
def test_real_middleware_preserves_response_when_monitor_setup_fails(monkeypatch, mode):
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_GUARD_MODE", mode)
    monkeypatch.setattr(
        middleware_module.ComputationMemoryMonitor,
        "_sample_and_emit",
        MagicMock(side_effect=RuntimeError("start failed")),
    )
    log = MagicMock()
    monkeypatch.setattr(middleware_module.logger, "error", log.error)

    response = Client().get("/model_builder/ok/")

    assert response.status_code == 200
    assert response.content == b"ok"
    errors = _monitor_errors(log)
    assert len(errors) == 1
    assert errors[0]["phase"] == "setup"
    assert errors[0]["route"] == "model_builder/ok/"
    assert errors[0]["mode"] == mode


@override_settings(
    ROOT_URLCONF=__name__,
    MIDDLEWARE=["e_footprint_interface.computation_memory_middleware.ComputationMemoryMiddleware"],
)
def test_real_middleware_disables_observation_after_reactive_callback_failure(monkeypatch):
    _patch_memory(monkeypatch)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_GUARD_MODE", "observe")
    callback = MagicMock(side_effect=RuntimeError("callback failed"))
    monkeypatch.setattr(middleware_module.ComputationMemoryMonitor, "__call__", callback)

    @contextmanager
    def trigger_callbacks(observer):
        observer(SimpleNamespace(diagnostic_name="slot"))
        observer(SimpleNamespace(diagnostic_name="slot"))
        yield

    monkeypatch.setattr(middleware_module, "observe_computations", trigger_callbacks)
    log = MagicMock()
    monkeypatch.setattr(middleware_module.logger, "info", log.info)
    monkeypatch.setattr(middleware_module.logger, "error", log.error)

    response = Client().get("/model_builder/ok/")

    assert response.status_code == 200
    assert response.content == b"ok"
    callback.assert_called_once()
    errors = _monitor_errors(log)
    assert len(errors) == 1
    assert errors[0]["phase"] == "computation_callback"


def test_enforce_boundary_keeps_typed_capacity_exception_path(monkeypatch):
    _patch_memory(monkeypatch)
    exception = ComputationMemoryLimitExceeded(working_set_bytes=3900, limit_bytes=3800, capacity_bytes=4096)
    callback = MagicMock(side_effect=exception)
    monitor = middleware_module.ComputationMemoryMonitor(
        route="model_builder/results/", method="GET", mode="enforce", log=MagicMock()
    )
    boundary = middleware_module._TelemetryBoundary(monitor)

    with pytest.raises(ComputationMemoryLimitExceeded):
        boundary._run("computation_callback", callback, SimpleNamespace(diagnostic_name="slot"))


def test_enforce_mode_fails_open_after_unexpected_monitor_error(monkeypatch):
    _patch_memory(monkeypatch)
    monitor = middleware_module.ComputationMemoryMonitor(
        route="model_builder/results/", method="GET", mode="enforce", log=MagicMock()
    )
    monitor._sample_progress = MagicMock(side_effect=RuntimeError("telemetry failed"))
    boundary = middleware_module._TelemetryBoundary(monitor)

    for _ in range(32):
        boundary(SimpleNamespace(diagnostic_name="ordinary_slot"))

    assert boundary.failed is True
    monitor._sample_progress.assert_called_once()


@override_settings(
    ROOT_URLCONF=__name__,
    MIDDLEWARE=["e_footprint_interface.computation_memory_middleware.ComputationMemoryMiddleware"],
)
def test_undecorated_route_uses_generic_memory_limit_modal_fallback(monkeypatch):
    _patch_memory(monkeypatch)
    monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_GUARD_MODE", "enforce")
    log = MagicMock()
    monkeypatch.setattr(middleware_module.logger, "info", log.info)

    response = Client().get("/model_builder/capacity-fail/")

    body = response.content.decode()
    assert response.status_code == 200
    assert response.headers["HX-Reswap"] == "none"
    assert ComputationMemoryLimitExceeded.safe_message in body
    records = _records(log)
    assert [record["event"] for record in records] == ["start", "abort"]
    assert len({record["request_id"] for record in records}) == 1


@override_settings(
    ROOT_URLCONF=__name__,
    MIDDLEWARE=[
        "django.contrib.sessions.middleware.SessionMiddleware",
        "e_footprint_interface.computation_memory_middleware.ComputationMemoryMiddleware",
    ],
)
@pytest.mark.django_db
def test_memory_limited_export_preserves_persisted_model(monkeypatch, minimal_system_data):
    _patch_memory(monkeypatch)
    monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_GUARD_MODE", "enforce")
    client = Client()
    repository = SessionSystemRepository(client.session)
    repository.save_data(minimal_system_data)
    persisted_before = repository.get_system_data()
    exception = ComputationMemoryLimitExceeded(
        working_set_bytes=3500 * runtime_memory.MIB,
        limit_bytes=3400 * runtime_memory.MIB,
        capacity_bytes=4096 * runtime_memory.MIB,
    )
    monkeypatch.setattr(views.ModelWeb, "export_json", MagicMock(side_effect=exception))

    response = client.get("/model_builder/download-json/")

    assert response.status_code == 200
    assert ComputationMemoryLimitExceeded.safe_message in response.content.decode()
    assert SessionSystemRepository(client.session).get_system_data() == persisted_before


@override_settings(
    ROOT_URLCONF=__name__,
    MIDDLEWARE=["e_footprint_interface.computation_memory_middleware.ComputationMemoryMiddleware"],
)
def test_real_middleware_preserves_response_when_completion_record_fails(monkeypatch):
    _patch_memory(monkeypatch)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_GUARD_MODE", "observe")
    log = MagicMock()

    def fail_completion_record(_message, payload):
        if json.loads(payload)["event"] == "complete":
            raise RuntimeError("logging failed")

    log.info.side_effect = fail_completion_record
    monkeypatch.setattr(middleware_module.logger, "info", log.info)
    monkeypatch.setattr(middleware_module.logger, "error", log.error)

    response = Client().get("/model_builder/ok/")

    assert response.status_code == 200
    assert response.content == b"ok"
    errors = _monitor_errors(log)
    assert len(errors) == 1
    assert errors[0]["phase"] == "finish"


@override_settings(
    ROOT_URLCONF=__name__,
    MIDDLEWARE=["e_footprint_interface.computation_memory_middleware.ComputationMemoryMiddleware"],
)
def test_real_middleware_finish_failure_does_not_mask_application_exception(monkeypatch):
    _patch_memory(monkeypatch)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_GUARD_MODE", "observe")
    monkeypatch.setattr(
        middleware_module.ComputationMemoryMonitor,
        "finish",
        MagicMock(side_effect=RuntimeError("finish failed")),
    )
    log = MagicMock()
    monkeypatch.setattr(middleware_module.logger, "info", log.info)
    monkeypatch.setattr(middleware_module.logger, "error", log.error)

    with pytest.raises(RuntimeError, match="boom"):
        Client().get("/model_builder/fail/")

    errors = _monitor_errors(log)
    assert len(errors) == 1
    assert errors[0]["phase"] == "finish"


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
