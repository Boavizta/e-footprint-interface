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
    process = MagicMock()
    process.memory_info.return_value.rss = memory_mb * 1024 * 1024
    monkeypatch.setattr(config.psutil, "Process", MagicMock(return_value=process))
    return gc


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
        memory_mb=gunicorn_config.MEMORY_LIMIT_MB + 1,
    )

    gunicorn_config.pre_request(worker, MagicMock())
    gunicorn_config.post_request(worker, MagicMock(), {}, MagicMock())

    gc.enable.assert_not_called()
    assert worker.alive is False


def test_restores_gc_when_post_request_memory_check_fails(monkeypatch, gunicorn_config):
    worker = _worker()
    gc = _configure_runtime(monkeypatch, gunicorn_config)
    gunicorn_config.pre_request(worker, MagicMock())
    gunicorn_config.psutil.Process.side_effect = RuntimeError("unavailable")

    with pytest.raises(RuntimeError, match="unavailable"):
        gunicorn_config.post_request(worker, MagicMock(), {}, MagicMock())

    gc.enable.assert_called_once_with()
