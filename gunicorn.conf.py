# Gunicorn configuration file
import gc
import os
from pathlib import Path
from time import perf_counter, process_time

import psutil

preload_app = True
log_file = "-"
bind = "0.0.0.0:8000"
workers = 1
timeout = 120

_MIB = 1024 * 1024
_CGROUP_LIMIT_PATHS = (Path("/sys/fs/cgroup/memory.max"), Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"))
_CGROUP_USAGE_PATHS = (Path("/sys/fs/cgroup/memory.current"), Path("/sys/fs/cgroup/memory/memory.usage_in_bytes"))


def _read_first_finite_value(paths):
    for path in paths:
        try:
            raw_value = path.read_text().strip()
            if raw_value != "max":
                value = int(raw_value)
                # Cgroup v1 represents an unlimited controller with a very large sentinel value.
                if value < 1 << 60:
                    return value
        except (OSError, ValueError):
            continue
    return None


def _memory_limit_mb():
    absolute_limit = os.getenv("WORKER_MEMORY_LIMIT_MB")
    if absolute_limit is not None:
        limit_mb = float(absolute_limit)
        if limit_mb <= 0:
            raise ValueError("WORKER_MEMORY_LIMIT_MB must be positive")
        return limit_mb

    ratio = float(os.getenv("WORKER_MEMORY_LIMIT_RATIO", "0.8"))
    if not 0 < ratio < 1:
        raise ValueError("WORKER_MEMORY_LIMIT_RATIO must be between 0 and 1")
    available_bytes = _read_first_finite_value(_CGROUP_LIMIT_PATHS) or psutil.virtual_memory().total
    return available_bytes / _MIB * ratio


def _memory_usage_mb():
    used_bytes = _read_first_finite_value(_CGROUP_USAGE_PATHS)
    return used_bytes / _MIB if used_bytes is not None else psutil.Process(os.getpid()).memory_info().rss / _MIB


MEMORY_LIMIT_MB = _memory_limit_mb()


def pre_request(worker, req):
    """Keep cyclic GC from introducing an unpredictable pause while serving a request."""
    worker._efootprint_gc_was_enabled = gc.isenabled()
    gc.disable()


def post_request(worker, req, environ, resp):
    """Collect request garbage after its response, then enforce the worker memory limit."""
    try:
        wall_started_at = perf_counter()
        cpu_started_at = process_time()
        collected = gc.collect()
        wall_ms = 1000 * (perf_counter() - wall_started_at)
        cpu_ms = 1000 * (process_time() - cpu_started_at)
        worker.log.info(
            f"Post-request full GC collected {collected} objects in {wall_ms:.1f} ms "
            f"(CPU {cpu_ms:.1f} ms, pid={os.getpid()})."
        )

        memory_mb = _memory_usage_mb()
        if memory_mb > MEMORY_LIMIT_MB:
            worker.log.warning(
                f"Recycling worker because memory usage is {memory_mb:.1f} MB, above the "
                f"{MEMORY_LIMIT_MB:.1f} MB limit (pid={os.getpid()})."
            )
            worker.alive = False
    finally:
        if getattr(worker, "_efootprint_gc_was_enabled", True):
            gc.enable()
