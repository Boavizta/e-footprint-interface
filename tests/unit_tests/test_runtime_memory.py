from pathlib import Path
from unittest.mock import MagicMock

import pytest

from e_footprint_interface import runtime_memory


def _file(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content)
    return path


def test_cgroup_capacity_supports_v2_v1_and_unlimited_values(tmp_path):
    unlimited = _file(tmp_path, "unlimited", "max")
    v1_unlimited = _file(tmp_path, "v1-unlimited", str(1 << 62))
    finite = _file(tmp_path, "finite", str(4 * 1024**3))

    assert runtime_memory.read_cgroup_capacity_bytes((unlimited, v1_unlimited, finite)) == 4 * 1024**3
    assert runtime_memory.read_cgroup_capacity_bytes((unlimited, v1_unlimited)) is None


def test_snapshot_distinguishes_raw_usage_inactive_file_working_set_and_rss(monkeypatch):
    monkeypatch.setattr(runtime_memory, "read_cgroup_current_bytes", MagicMock(return_value=1400 * runtime_memory.MIB))
    monkeypatch.setattr(runtime_memory, "read_inactive_file_bytes", MagicMock(return_value=1100 * runtime_memory.MIB))
    monkeypatch.setattr(runtime_memory, "read_process_rss_bytes", MagicMock(return_value=250 * runtime_memory.MIB))
    monkeypatch.setattr(runtime_memory, "CGROUP_CAPACITY_BYTES", 4096 * runtime_memory.MIB)

    snapshot = runtime_memory.read_memory_snapshot()

    assert snapshot.working_set_bytes == 300 * runtime_memory.MIB
    assert snapshot.as_mebibytes() == {
        "rss_mb": 250.0,
        "cgroup_current_mb": 1400.0,
        "inactive_file_mb": 1100.0,
        "working_set_mb": 300.0,
        "capacity_mb": 4096.0,
    }


def test_v1_inactive_file_uses_hierarchical_total_when_both_values_exist(tmp_path):
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    stat = _file(memory_dir, "memory.stat", "inactive_file 10\ntotal_inactive_file 110\n")

    assert runtime_memory.read_inactive_file_bytes((stat,)) == 110


def test_lightweight_working_set_does_not_read_process_rss(monkeypatch):
    monkeypatch.setattr(runtime_memory, "read_cgroup_current_bytes", MagicMock(return_value=1400))
    monkeypatch.setattr(runtime_memory, "read_inactive_file_bytes", MagicMock(return_value=1100))
    rss_reader = MagicMock()
    monkeypatch.setattr(runtime_memory, "read_process_rss_bytes", rss_reader)

    assert runtime_memory.read_cgroup_working_set_bytes() == 300
    rss_reader.assert_not_called()

    snapshot = runtime_memory.read_memory_snapshot(include_process_rss=False)
    assert snapshot.rss_bytes is None
    assert snapshot.working_set_bytes == 300
    rss_reader.assert_not_called()


def test_snapshot_leaves_incomplete_cgroup_metrics_unavailable(monkeypatch):
    monkeypatch.setattr(runtime_memory, "read_cgroup_current_bytes", MagicMock(return_value=None))
    monkeypatch.setattr(runtime_memory, "read_inactive_file_bytes", MagicMock(return_value=10))
    monkeypatch.setattr(runtime_memory, "read_process_rss_bytes", MagicMock(return_value=20))

    snapshot = runtime_memory.read_memory_snapshot()

    assert snapshot.cgroup_current_bytes is None
    assert snapshot.working_set_bytes is None
    assert snapshot.rss_bytes == 20


def test_memory_events_reads_v2_and_v1_fallback(tmp_path):
    v2 = _file(tmp_path, "events", "low 1\nhigh 2\noom 3\noom_kill 2\n")
    missing = tmp_path / "missing"
    failcnt = _file(tmp_path, "failcnt", "7")

    assert runtime_memory.read_memory_events((v2,), (failcnt,))["oom_kill"] == 2
    assert runtime_memory.read_memory_events((missing,), (failcnt,)) == {
        "oom": None,
        "oom_kill": None,
        "failcnt": 7,
    }
    assert runtime_memory.read_memory_events((missing,), (missing,)) == {"oom": None, "oom_kill": None}


@pytest.mark.parametrize("mode", ["off", "observe", "enforce", " OBSERVE "])
def test_guard_mode_accepts_supported_values(mode):
    assert runtime_memory.parse_guard_mode(mode) == mode.strip().lower()


def test_guard_mode_defaults_off_and_rejects_unknown(monkeypatch):
    monkeypatch.delenv("COMPUTATION_MEMORY_GUARD_MODE", raising=False)
    assert runtime_memory.parse_guard_mode() == "off"
    with pytest.raises(ValueError, match="off, observe, enforce"):
        runtime_memory.parse_guard_mode("enabled")


def test_memory_limit_prefers_absolute_override(monkeypatch):
    monkeypatch.setenv("TEST_LIMIT_MB", "2300")
    monkeypatch.setenv("TEST_LIMIT_RATIO", "0.5")

    limit = runtime_memory.resolve_memory_limit_bytes(
        4096 * runtime_memory.MIB,
        absolute_name="TEST_LIMIT_MB",
        ratio_name="TEST_LIMIT_RATIO",
        default_ratio=0.8,
    )

    assert limit == 2300 * runtime_memory.MIB


def test_computation_memory_limit_keeps_eighty_five_percent_default():
    assert runtime_memory.DEFAULT_COMPUTATION_MEMORY_LIMIT_RATIO == 0.85


def test_memory_limit_uses_ratio_and_validates_it(monkeypatch):
    monkeypatch.delenv("TEST_LIMIT_MB", raising=False)
    monkeypatch.setenv("TEST_LIMIT_RATIO", "0.6")
    assert runtime_memory.resolve_memory_limit_bytes(
        4096 * runtime_memory.MIB,
        absolute_name="TEST_LIMIT_MB",
        ratio_name="TEST_LIMIT_RATIO",
        default_ratio=0.8,
    ) == int(4096 * runtime_memory.MIB * 0.6)

    monkeypatch.setenv("TEST_LIMIT_RATIO", "1")
    with pytest.raises(ValueError, match="between 0 and 1"):
        runtime_memory.resolve_memory_limit_bytes(
            None,
            absolute_name="TEST_LIMIT_MB",
            ratio_name="TEST_LIMIT_RATIO",
            default_ratio=0.8,
        )
