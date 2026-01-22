# Gunicorn configuration file
import multiprocessing

max_requests = 100
max_requests_jitter = 10
preload_app = True
log_file = "-"
bind = "0.0.0.0:8000"

workers = 2
threads = workers
timeout = 120
