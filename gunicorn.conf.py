# Gunicorn configuration file for production deployment
# Run with: gunicorn --config gunicorn.conf.py wsgi:app

import multiprocessing
import os
# Server socket
bind = "0.0.0.0:2001"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 100
preload_app = False  # Keep False due to our lazy initialization pattern
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')
accesslog = os.getenv('GUNICORN_ACCESS_LOG', '-')  # stdout
errorlog = os.getenv('GUNICORN_ERROR_LOG', '-')    # stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
proc_name = 'mlformentalhealth-app'
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
worker_tmp_dir = '/dev/shm'  # Use memory for worker temp files (Linux only)

# Graceful shutdown
graceful_timeout = 120

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("MLforMentalHealth app is ready to serve requests")

def worker_int(worker):
    """Called when a worker receives the SIGINT or SIGQUIT signal."""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info(f"Worker {worker.pid} is about to be forked")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker {worker.pid} has been forked")

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forked child, re-executing")

def on_exit(server):
    """Called just before exiting."""
    server.log.info("MLforMentalHealth app is shutting down")