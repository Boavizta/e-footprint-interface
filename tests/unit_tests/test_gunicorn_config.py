from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from e_footprint_interface import runtime_memory


@pytest.fixture
def gunicorn_config():
    config_path = Path(__file__).parents[2] / "gunicorn.conf.py"
    spec = spec_from_file_location("efootprint_gunicorn_config", config_path)
    config = module_from_spec(spec)
    spec.loader.exec_module(config)
    return config


def _worker():
    return SimpleNamespace(log=MagicMock(), alive=True, pid=36)


def _snapshot(working_set_mb=100):
    return runtime_memory.MemorySnapshot(
        rss_bytes=80 * runtime_memory.MIB,
        cgroup_current_bytes=(working_set_mb + 20) * runtime_memory.MIB,
        inactive_file_bytes=20 * runtime_memory.MIB,
        working_set_bytes=working_set_mb * runtime_memory.MIB,
        capacity_bytes=4096 * runtime_memory.MIB,
    )


def _configure_runtime(monkeypatch, config, *, gc_was_enabled=True, memory_mb=100):
    gc = MagicMock()
    gc.isenabled.return_value = gc_was_enabled
    gc.collect.return_value = 62936
    monkeypatch.setattr(config, "gc", gc)
    monkeypatch.setattr(config, "perf_counter", MagicMock(side_effect=(1.0, 1.2)))
    monkeypatch.setattr(config, "process_time", MagicMock(side_effect=(2.0, 2.18)))
    monkeypatch.setattr(config.os, "getpid", MagicMock(return_value=36))
    monkeypatch.setattr(config, "_memory_usage_mb", MagicMock(return_value=memory_mb))
    monkeypatch.setattr(config.runtime_memory, "read_memory_snapshot", MagicMock(return_value=_snapshot(memory_mb)))
    return gc


def test_worker_recycle_limit_keeps_sixty_percent_default():
    assert runtime_memory.WORKER_RECYCLE_LIMIT_BYTES == int(runtime_memory.THRESHOLD_CAPACITY_BYTES * 0.6)


def test_memory_usage_excludes_reclaimable_file_cache(monkeypatch, gunicorn_config):
    monkeypatch.setattr(gunicorn_config.runtime_memory, "read_memory_snapshot", MagicMock(return_value=_snapshot(300)))
    assert gunicorn_config._memory_usage_mb() == 300


def test_memory_usage_falls_back_to_worker_rss(monkeypatch, gunicorn_config):
    snapshot = runtime_memory.MemorySnapshot(250 * runtime_memory.MIB, None, None, None, None)
    monkeypatch.setattr(gunicorn_config.runtime_memory, "read_memory_snapshot", MagicMock(return_value=snapshot))
    assert gunicorn_config._memory_usage_mb() == 250


def test_worker_lifecycle_reports_oom_counter_deltas(monkeypatch, gunicorn_config):
    server = SimpleNamespace(log=MagicMock())
    worker = _worker()
    events = MagicMock(side_effect=({"oom": 4, "oom_kill": 1}, {"oom": 5, "oom_kill": 2}))
    monkeypatch.setattr(gunicorn_config.runtime_memory, "read_memory_events", events)
    monkeypatch.setattr(gunicorn_config.runtime_memory, "read_memory_snapshot", MagicMock(return_value=_snapshot()))

    gunicorn_config.pre_fork(server, worker)
    gunicorn_config.child_exit(server, worker)

    server.log.warning.assert_called_once()
    serialized = server.log.warning.call_args.args[1]
    assert '"oom": 1' in serialized
    assert '"oom_kill": 1' in serialized
    assert '"rss_mb"' not in serialized
    assert '"pid": 36' in serialized
    gunicorn_config.runtime_memory.read_memory_snapshot.assert_called_with(include_process_rss=False)


def test_worker_lifecycle_reports_v1_failcnt_without_claiming_an_oom_kill(monkeypatch, gunicorn_config):
    server = SimpleNamespace(log=MagicMock())
    worker = _worker()
    events = MagicMock(
        side_effect=(
            {"oom": None, "oom_kill": None, "failcnt": 4},
            {"oom": None, "oom_kill": None, "failcnt": 5},
        )
    )
    monkeypatch.setattr(gunicorn_config.runtime_memory, "read_memory_events", events)
    monkeypatch.setattr(gunicorn_config.runtime_memory, "read_memory_snapshot", MagicMock(return_value=_snapshot()))

    gunicorn_config.pre_fork(server, worker)
    gunicorn_config.child_exit(server, worker)

    serialized = server.log.warning.call_args.args[1]
    assert '"failcnt": 1' in serialized
    assert '"oom": null' in serialized
    assert '"oom_kill": null' in serialized


def test_worker_lifecycle_uses_info_when_no_oom_changed(monkeypatch, gunicorn_config):
    server = SimpleNamespace(log=MagicMock())
    worker = _worker()
    monkeypatch.setattr(gunicorn_config.runtime_memory, "read_memory_events", MagicMock(return_value={"oom": 4}))
    monkeypatch.setattr(gunicorn_config.runtime_memory, "read_memory_snapshot", MagicMock(return_value=_snapshot()))

    gunicorn_config.pre_fork(server, worker)
    gunicorn_config.child_exit(server, worker)

    server.log.info.assert_called_once()
    server.log.warning.assert_not_called()


def test_collects_after_response_logs_correlated_cost_and_restores_enabled_gc(monkeypatch, gunicorn_config):
    worker = _worker()
    gc = _configure_runtime(monkeypatch, gunicorn_config)

    gunicorn_config.pre_request(worker, MagicMock())
    gunicorn_config.post_request(worker, MagicMock(), {"efootprint.memory_request_id": "request-1"}, MagicMock())

    gc.disable.assert_called_once_with()
    gc.collect.assert_called_once_with()
    gc.enable.assert_called_once_with()
    assert worker.log.info.call_args.args[0] == "post_request_memory %s"
    assert '"request_id": "request-1"' in worker.log.info.call_args.args[1]
    assert worker.alive is True


def test_preserves_disabled_gc_and_still_enforces_recycling_threshold(monkeypatch, gunicorn_config):
    worker = _worker()
    gc = _configure_runtime(
        monkeypatch,
        gunicorn_config,
        gc_was_enabled=False,
        memory_mb=gunicorn_config.WORKER_RECYCLE_LIMIT_MB + 1,
    )

    gunicorn_config.pre_request(worker, MagicMock())
    gunicorn_config.post_request(worker, MagicMock(), {}, MagicMock())

    gc.enable.assert_not_called()
    assert worker.alive is False
    worker.log.warning.assert_called_once()


def test_restores_gc_when_post_request_memory_check_fails(monkeypatch, gunicorn_config):
    worker = _worker()
    gc = _configure_runtime(monkeypatch, gunicorn_config)
    gunicorn_config.pre_request(worker, MagicMock())
    gunicorn_config._memory_usage_mb.side_effect = RuntimeError("unavailable")

    with pytest.raises(RuntimeError, match="unavailable"):
        gunicorn_config.post_request(worker, MagicMock(), {}, MagicMock())

    gc.enable.assert_called_once_with()
