# Gunicorn configuration file
import gc
import json
import os
from time import perf_counter, process_time

from e_footprint_interface import runtime_memory


preload_app = True
log_file = "-"
bind = "0.0.0.0:8000"
workers = 1
timeout = 120

CONTAINER_MEMORY_MB = runtime_memory.THRESHOLD_CAPACITY_BYTES / runtime_memory.MIB
WORKER_RECYCLE_LIMIT_MB = runtime_memory.WORKER_RECYCLE_LIMIT_BYTES / runtime_memory.MIB


def _memory_usage_mb():
    snapshot = runtime_memory.read_memory_snapshot()
    bytes_used = snapshot.working_set_bytes if snapshot.working_set_bytes is not None else snapshot.rss_bytes
    return bytes_used / runtime_memory.MIB if bytes_used is not None else 0


def _event_delta(previous: dict[str, int], current: dict[str, int]) -> dict[str, int]:
    return {key: max(0, current.get(key, 0) - previous.get(key, 0)) for key in {"oom", "oom_kill"}}


def _worker_record(event, worker, *, events=None, event_delta=None):
    snapshot = runtime_memory.read_memory_snapshot()
    return {
        "event": event,
        "pid": getattr(worker, "pid", None),
        **snapshot.as_mebibytes(),
        "memory_events": events if events is not None else runtime_memory.read_memory_events(),
        "memory_event_delta": event_delta,
    }


def pre_fork(server, worker):
    """Capture counters in the master so they survive a worker SIGKILL."""
    worker._efootprint_memory_events_at_boot = runtime_memory.read_memory_events()


def post_fork(server, worker):
    events = runtime_memory.read_memory_events()
    worker.log.info(
        "worker_memory %s", json.dumps(_worker_record("worker_boot", worker, events=events), sort_keys=True)
    )


def child_exit(server, worker):
    events = runtime_memory.read_memory_events()
    previous = getattr(worker, "_efootprint_memory_events_at_boot", {})
    delta = _event_delta(previous, events)
    log = server.log.warning if delta["oom"] or delta["oom_kill"] else server.log.info
    log(
        "worker_memory %s",
        json.dumps(_worker_record("worker_exit", worker, events=events, event_delta=delta), sort_keys=True),
    )


def pre_request(worker, req):
    """Keep cyclic GC from introducing an unpredictable pause while serving a request."""
    worker._efootprint_gc_was_enabled = gc.isenabled()
    gc.disable()


def post_request(worker, req, environ, resp):
    """Collect request garbage after its response, then enforce the worker recycling threshold."""
    try:
        wall_started_at = perf_counter()
        cpu_started_at = process_time()
        collected = gc.collect()
        wall_ms = 1000 * (perf_counter() - wall_started_at)
        cpu_ms = 1000 * (process_time() - cpu_started_at)
        request_id = environ.get("efootprint.memory_request_id")
        worker.log.info(
            "post_request_memory %s",
            json.dumps(
                {
                    "request_id": request_id,
                    "pid": os.getpid(),
                    "gc_collected": collected,
                    "gc_wall_ms": round(wall_ms, 1),
                    "gc_cpu_ms": round(cpu_ms, 1),
                    **runtime_memory.read_memory_snapshot().as_mebibytes(),
                },
                sort_keys=True,
            ),
        )

        memory_mb = _memory_usage_mb()
        if memory_mb > WORKER_RECYCLE_LIMIT_MB:
            worker.log.warning(
                "Recycling worker because memory working set is %.1f MB, above the %.1f MB recycling threshold "
                "(pid=%s, request_id=%s).",
                memory_mb,
                WORKER_RECYCLE_LIMIT_MB,
                os.getpid(),
                request_id,
            )
            worker.alive = False
    finally:
        if getattr(worker, "_efootprint_gc_was_enabled", True):
            gc.enable()
