"""Gunicorn configuration file for FastAPI application."""

bind = "0.0.0.0:5000"
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
reload = True
preload_app = True

# Application module and callable
wsgi_app = "main:app"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

def on_starting(server):
    server.log.info("Starting FastAPI application with uvicorn workers")

def worker_int(worker):
    worker.log.info("Worker interrupted")