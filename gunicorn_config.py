"""Gunicorn configuration file for Flask application."""

# Import our main app
import main_app

bind = "0.0.0.0:5000" 
workers = 1
worker_class = "sync"  # Using standard synchronous worker for Flask

# Specify the application
wsgi_app = "app:app"
reload = True