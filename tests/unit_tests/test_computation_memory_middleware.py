import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

from django.http import HttpResponse
from django.test import RequestFactory
import pytest

from e_footprint_interface import runtime_memory
from e_footprint_interface import computation_memory_middleware as middleware_module


def _snapshot(working_set_mb=100, *, current_mb=120, inactive_mb=20, rss_mb=80, capacity_mb=4096):
    return runtime_memory.MemorySnapshot(
        rss_bytes=rss_mb * runtime_memory.MIB,
        cgroup_current_bytes=current_mb * runtime_memory.MIB,
        inactive_file_bytes=inactive_mb * runtime_memory.MIB,
        working_set_bytes=working_set_mb * runtime_memory.MIB,
        capacity_bytes=capacity_mb * runtime_memory.MIB,
    )


def _records(log):
    return [json.loads(call.args[1]) for call in log.info.call_args_list]


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
    reader = MagicMock(return_value=_snapshot())
    monkeypatch.setattr(runtime_memory, "read_memory_snapshot", reader)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_LIMIT_BYTES", 4000 * runtime_memory.MIB)
    monitor = middleware_module.ComputationMemoryMonitor(route="model_builder/", method="GET", log=MagicMock())

    for _ in range(15):
        monitor(SimpleNamespace(diagnostic_name="footprint"))
    assert reader.call_count == 1

    monitor(SimpleNamespace(diagnostic_name="footprint"))
    assert reader.call_count == 2
    assert monitor.completed_slots == 16


@pytest.mark.parametrize("mode", ["observe", "enforce"])
def test_monitor_samples_every_callback_near_limit_but_never_raises(monkeypatch, mode):
    reader = MagicMock(return_value=_snapshot(working_set_mb=3800))
    monkeypatch.setattr(runtime_memory, "read_memory_snapshot", reader)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_LIMIT_BYTES", 3900 * runtime_memory.MIB)
    monitor = middleware_module.ComputationMemoryMonitor(
        route="model_builder/sankey-diagram/", method="GET", mode=mode, log=MagicMock()
    )

    for _ in range(3):
        monitor(SimpleNamespace(diagnostic_name="impact_repartition_rows"))

    assert reader.call_count == 4
    assert monitor.completed_slots == 3


def test_progress_logs_only_new_high_water_bands_and_large_jump_identity(monkeypatch):
    reader = MagicMock(
        side_effect=[
            _snapshot(100),
            _snapshot(120),
            _snapshot(230),
            _snapshot(400),
        ]
    )
    monkeypatch.setattr(runtime_memory, "read_memory_snapshot", reader)
    monkeypatch.setattr(runtime_memory, "COMPUTATION_MEMORY_LIMIT_BYTES", 200 * runtime_memory.MIB)
    log = MagicMock()
    monitor = middleware_module.ComputationMemoryMonitor(route="model_builder/results/", method="GET", log=log)
    monitor(SimpleNamespace(diagnostic_name="ordinary_slot"))
    monitor(SimpleNamespace(diagnostic_name="another_slot"))
    monitor(SimpleNamespace(diagnostic_name="impact_repartition_rows"))

    records = _records(log)
    progress = [record for record in records if record["event"] == "progress"]
    assert len(progress) == 2
    assert "slot" not in progress[0]
    assert progress[1]["slot"] == "impact_repartition_rows"


def test_completion_record_is_correlated_privacy_safe_and_reports_overhead(monkeypatch):
    monkeypatch.setattr(runtime_memory, "read_memory_snapshot", MagicMock(return_value=_snapshot()))
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
