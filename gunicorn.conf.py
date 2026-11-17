# gunicorn.conf.py - Production WSGI server configuration (R-06)
import multiprocessing
import os

# Server socket
bind = os.environ.get('GUNICORN_BIND', f"0.0.0.0:{os.environ.get('PORT', '8000')}")
backlog = 2048

# Worker processes & threading
workers = int(os.environ.get('WEB_CONCURRENCY', os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1)))
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'gthread')
threads = int(os.environ.get('GUNICORN_THREADS', '2'))
worker_connections = 1000
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '60'))
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', '5'))
graceful_timeout = 30

# Worker recycling to mitigate memory leaks
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', '1000'))
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', '100'))

# Logging
accesslog = '-'
errorlog = '-'
loglevel = os.environ.get('LOG_LEVEL', 'info').lower()
access_log_format = (
    '{"remote_ip":"%(h)s","request_time":"%(t)s","method":"%(m)s","path":"%(U)s",'
    '"status":"%(s)s","response_length":"%(B)s","latency_ms":"%(D)s","referer":"%(f)s"}'
)

# Process naming
proc_name = 'hedgewar-hms'


def on_starting(server):
    server.log.info("Hedgewar Hospital Care Gunicorn server starting...")


def post_fork(server, worker):
    server.log.info(f"Worker spawned (pid: {worker.pid})")


def worker_exit(server, worker):
    server.log.info(f"Worker exiting (pid: {worker.pid})")
