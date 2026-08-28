"""Low-overhead process and cgroup memory readings shared by Django and Gunicorn."""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable

import psutil


MIB = 1024 * 1024
_CGROUP_UNLIMITED_SENTINEL = 1 << 60

CGROUP_CAPACITY_PATHS = (
    Path("/sys/fs/cgroup/memory.max"),
    Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"),
)
CGROUP_CURRENT_PATHS = (
    Path("/sys/fs/cgroup/memory.current"),
    Path("/sys/fs/cgroup/memory/memory.usage_in_bytes"),
)
CGROUP_STAT_PATHS = (
    Path("/sys/fs/cgroup/memory.stat"),
    Path("/sys/fs/cgroup/memory/memory.stat"),
)
CGROUP_EVENT_PATHS = (Path("/sys/fs/cgroup/memory.events"),)
CGROUP_V1_FAILCNT_PATHS = (Path("/sys/fs/cgroup/memory/memory.failcnt"),)


@dataclass(frozen=True)
class MemorySnapshot:
    """One coherent-enough diagnostic sample; individual unavailable fields remain ``None``."""

    rss_bytes: int | None
    cgroup_current_bytes: int | None
    inactive_file_bytes: int | None
    working_set_bytes: int | None
    capacity_bytes: int | None

    def as_mebibytes(self) -> dict[str, float | None]:
        return {
            "rss_mb": _to_mib(self.rss_bytes),
            "cgroup_current_mb": _to_mib(self.cgroup_current_bytes),
            "inactive_file_mb": _to_mib(self.inactive_file_bytes),
            "working_set_mb": _to_mib(self.working_set_bytes),
            "capacity_mb": _to_mib(self.capacity_bytes),
        }


def _to_mib(value: int | None) -> float | None:
    return round(value / MIB, 1) if value is not None else None


def _read_first_integer(paths: Iterable[Path], *, finite: bool = False) -> int | None:
    for path in paths:
        try:
            raw_value = path.read_text(encoding="utf-8").strip()
            if raw_value == "max":
                continue
            value = int(raw_value)
            if value < 0 or (finite and value >= _CGROUP_UNLIMITED_SENTINEL):
                continue
            return value
        except (OSError, ValueError):
            continue
    return None


def read_cgroup_capacity_bytes(paths: Iterable[Path] = CGROUP_CAPACITY_PATHS) -> int | None:
    """Return the finite cgroup limit, or ``None`` for unavailable/unlimited controllers."""
    return _read_first_integer(paths, finite=True)


def read_cgroup_current_bytes(paths: Iterable[Path] = CGROUP_CURRENT_PATHS) -> int | None:
    return _read_first_integer(paths)


def read_inactive_file_bytes(paths: Iterable[Path] = CGROUP_STAT_PATHS) -> int | None:
    for path in paths:
        try:
            values = dict(line.split() for line in path.read_text(encoding="utf-8").splitlines())
            key = "inactive_file" if "inactive_file" in values else "total_inactive_file"
            return int(values[key])
        except (KeyError, OSError, ValueError):
            continue
    return None


def read_cgroup_working_set_bytes() -> int | None:
    """Return non-reclaimable cgroup usage without collecting process diagnostics."""
    current = read_cgroup_current_bytes()
    inactive_file = read_inactive_file_bytes()
    if current is None or inactive_file is None:
        return None
    return max(0, current - inactive_file)


def read_process_rss_bytes(process: psutil.Process | None = None) -> int | None:
    try:
        return (process or psutil.Process(os.getpid())).memory_info().rss
    except (OSError, psutil.Error):
        return None


def read_memory_snapshot(process: psutil.Process | None = None) -> MemorySnapshot:
    current = read_cgroup_current_bytes()
    inactive_file = read_inactive_file_bytes()
    working_set = max(0, current - inactive_file) if current is not None and inactive_file is not None else None
    return MemorySnapshot(
        rss_bytes=read_process_rss_bytes(process),
        cgroup_current_bytes=current,
        inactive_file_bytes=inactive_file,
        working_set_bytes=working_set,
        capacity_bytes=CGROUP_CAPACITY_BYTES,
    )


def _read_key_value_file(path: Path) -> dict[str, int] | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        return {key: int(value) for key, value in (line.split() for line in lines)}
    except (OSError, ValueError):
        return None


def read_memory_events(
    event_paths: Iterable[Path] = CGROUP_EVENT_PATHS,
    v1_failcnt_paths: Iterable[Path] = CGROUP_V1_FAILCNT_PATHS,
) -> dict[str, int]:
    """Read cumulative OOM evidence from cgroup v2, with v1 failcnt as the available equivalent."""
    for path in event_paths:
        events = _read_key_value_file(path)
        if events is not None:
            return events
    failcnt = _read_first_integer(v1_failcnt_paths)
    return {"oom": failcnt, "oom_kill": 0} if failcnt is not None else {}


def parse_guard_mode(value: str | None = None) -> str:
    mode = (value if value is not None else os.getenv("COMPUTATION_MEMORY_GUARD_MODE", "off")).strip().lower()
    if mode not in {"off", "observe", "enforce"}:
        raise ValueError("COMPUTATION_MEMORY_GUARD_MODE must be one of: off, observe, enforce")
    return mode


def _positive_float_environment(name: str) -> float | None:
    raw_value = os.getenv(name)
    if raw_value is None:
        return None
    value = float(raw_value)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def resolve_memory_limit_bytes(
    capacity_bytes: int | None,
    *,
    absolute_name: str,
    ratio_name: str,
    default_ratio: float,
) -> int | None:
    absolute_mb = _positive_float_environment(absolute_name)
    if absolute_mb is not None:
        return int(absolute_mb * MIB)
    ratio = float(os.getenv(ratio_name, str(default_ratio)))
    if not 0 < ratio < 1:
        raise ValueError(f"{ratio_name} must be between 0 and 1")
    return int(capacity_bytes * ratio) if capacity_bytes is not None else None


def _threshold_capacity_bytes() -> int:
    """Preserve useful non-container behavior while keeping reported container capacity explicit."""
    return CGROUP_CAPACITY_BYTES or psutil.virtual_memory().total


CGROUP_CAPACITY_BYTES = read_cgroup_capacity_bytes()
THRESHOLD_CAPACITY_BYTES = _threshold_capacity_bytes()
COMPUTATION_MEMORY_LIMIT_BYTES = resolve_memory_limit_bytes(
    THRESHOLD_CAPACITY_BYTES,
    absolute_name="COMPUTATION_MEMORY_LIMIT_MB",
    ratio_name="COMPUTATION_MEMORY_LIMIT_RATIO",
    default_ratio=0.8,
)
WORKER_RECYCLE_LIMIT_BYTES = resolve_memory_limit_bytes(
    THRESHOLD_CAPACITY_BYTES,
    absolute_name="WORKER_RECYCLE_LIMIT_MB",
    ratio_name="WORKER_RECYCLE_LIMIT_RATIO",
    default_ratio=0.6,
)
COMPUTATION_MEMORY_GUARD_MODE = parse_guard_mode()
