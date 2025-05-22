"""Gunicorn configuration file with Uvicorn workers for FastAPI."""

bind = "0.0.0.0:5000" 
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"
reload = True