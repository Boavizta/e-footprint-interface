# Gunicorn configuration file
import gc
import os
from time import perf_counter, process_time

import psutil

preload_app = True
log_file = "-"
bind = "0.0.0.0:8000"
workers = 1
timeout = 120

MEMORY_LIMIT_MB = 1600  # 1.6 GB (80% of 2 GB instance)


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

        memory_mb = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        if memory_mb > MEMORY_LIMIT_MB:
            worker.alive = False
    finally:
        if getattr(worker, "_efootprint_gc_was_enabled", True):
            gc.enable()
