"""Gunicorn configuration file for FastAPI application."""

bind = "0.0.0.0:5000" 
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"  # Using uvicorn worker for FastAPI/ASGI

# Specify the application
application = "main:app"
reload = True