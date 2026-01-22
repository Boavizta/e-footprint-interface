# Gunicorn configuration file
import os
import psutil

preload_app = True
log_file = "-"
bind = "0.0.0.0:8000"
workers = 1
timeout = 120

MEMORY_LIMIT_MB = 1600  # 1.6 GB (80% of 2 GB instance)


def post_request(worker, req, environ, resp):
    """Restart worker when memory usage exceeds threshold."""
    memory_mb = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    if memory_mb > MEMORY_LIMIT_MB:
        worker.alive = False
