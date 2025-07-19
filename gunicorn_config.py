"""Gunicorn configuration file for FastAPI application."""

bind = "0.0.0.0:5000" 
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"  # Using uvicorn worker for FastAPI/ASGI
timeout = 120
keepalive = 5

# Specify the application
wsgi_app = "main:app"
reload = True

# Force ASGI compatibility
def on_starting(server):
    server.log.info("Starting FastAPI with ASGI uvicorn workers")