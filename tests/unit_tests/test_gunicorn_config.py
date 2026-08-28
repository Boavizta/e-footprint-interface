from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def gunicorn_config():
    config_path = Path(__file__).parents[2] / "gunicorn.conf.py"
    spec = spec_from_file_location("efootprint_gunicorn_config", config_path)
    config = module_from_spec(spec)
    spec.loader.exec_module(config)
    return config


def _worker():
    return SimpleNamespace(log=MagicMock(), alive=True)


def _configure_runtime(monkeypatch, config, *, gc_was_enabled=True, memory_mb=100):
    gc = MagicMock()
    gc.isenabled.return_value = gc_was_enabled
    gc.collect.return_value = 62936
    monkeypatch.setattr(config, "gc", gc)
    monkeypatch.setattr(config, "perf_counter", MagicMock(side_effect=(1.0, 1.2)))
    monkeypatch.setattr(config, "process_time", MagicMock(side_effect=(2.0, 2.18)))
    monkeypatch.setattr(config.os, "getpid", MagicMock(return_value=36))
    monkeypatch.setattr(config, "_memory_usage_mb", MagicMock(return_value=memory_mb))
    return gc


def test_container_memory_uses_cgroup_limit(monkeypatch, gunicorn_config):
    monkeypatch.setattr(gunicorn_config, "_read_first_finite_value", MagicMock(return_value=4 * 1024**3))

    assert gunicorn_config._container_memory_mb() == 4096


def test_worker_recycle_limit_uses_default_ratio(monkeypatch, gunicorn_config):
    monkeypatch.delenv("WORKER_RECYCLE_LIMIT_MB", raising=False)
    monkeypatch.delenv("WORKER_RECYCLE_LIMIT_RATIO", raising=False)

    assert gunicorn_config._worker_recycle_limit_mb(4096) == pytest.approx(2457.6)


def test_worker_recycle_limit_environment_overrides_default(monkeypatch, gunicorn_config):
    monkeypatch.setenv("WORKER_RECYCLE_LIMIT_MB", "2300")

    assert gunicorn_config._worker_recycle_limit_mb(4096) == 2300


def test_worker_recycle_limit_ratio_is_configurable(monkeypatch, gunicorn_config):
    monkeypatch.delenv("WORKER_RECYCLE_LIMIT_MB", raising=False)
    monkeypatch.setenv("WORKER_RECYCLE_LIMIT_RATIO", "0.5")

    assert gunicorn_config._worker_recycle_limit_mb(4096) == 2048


def test_memory_usage_excludes_reclaimable_cgroup_file_cache(monkeypatch, gunicorn_config):
    monkeypatch.setattr(gunicorn_config, "_read_first_finite_value", MagicMock(return_value=1400 * 1024**2))
    monkeypatch.setattr(gunicorn_config, "_inactive_file_bytes", MagicMock(return_value=1100 * 1024**2))

    assert gunicorn_config._memory_usage_mb() == 300


def test_memory_usage_falls_back_to_worker_rss_without_complete_cgroup_metrics(monkeypatch, gunicorn_config):
    monkeypatch.setattr(gunicorn_config, "_read_first_finite_value", MagicMock(return_value=None))
    process = MagicMock()
    process.memory_info.return_value.rss = 250 * 1024**2
    monkeypatch.setattr(gunicorn_config.psutil, "Process", MagicMock(return_value=process))

    assert gunicorn_config._memory_usage_mb() == 250


def test_collects_after_response_logs_cost_and_restores_enabled_gc(monkeypatch, gunicorn_config):
    worker = _worker()
    gc = _configure_runtime(monkeypatch, gunicorn_config)

    gunicorn_config.pre_request(worker, MagicMock())
    gunicorn_config.post_request(worker, MagicMock(), {}, MagicMock())

    gc.disable.assert_called_once_with()
    gc.collect.assert_called_once_with()
    gc.enable.assert_called_once_with()
    worker.log.info.assert_called_once_with(
        "Post-request full GC collected 62936 objects in 200.0 ms (CPU 180.0 ms, pid=36)."
    )
    assert worker.alive is True


def test_preserves_disabled_gc_and_still_enforces_memory_limit(monkeypatch, gunicorn_config):
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
    worker.log.warning.assert_called_once_with(
        f"Recycling worker because memory working set is {gunicorn_config.WORKER_RECYCLE_LIMIT_MB + 1:.1f} MB, "
        f"above the {gunicorn_config.WORKER_RECYCLE_LIMIT_MB:.1f} MB recycling threshold (pid=36)."
    )


def test_restores_gc_when_post_request_memory_check_fails(monkeypatch, gunicorn_config):
    worker = _worker()
    gc = _configure_runtime(monkeypatch, gunicorn_config)
    gunicorn_config.pre_request(worker, MagicMock())
    gunicorn_config._memory_usage_mb.side_effect = RuntimeError("unavailable")

    with pytest.raises(RuntimeError, match="unavailable"):
        gunicorn_config.post_request(worker, MagicMock(), {}, MagicMock())

    gc.enable.assert_called_once_with()
