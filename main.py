# Main entry point for gunicorn: main:app
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    "pool_recycle": 300,
}

# Initialize database
db = SQLAlchemy(app, model_class=Base)

# Create tables and import everything
with app.app_context():
    import models
    import auth
    import routes
    import user_routes
    import admin_routes
    from filters import timeago
    
    # Register filters
    app.jinja_env.filters['timeago'] = timeago
    
    # Create database tables
    db.create_all()
    logging.info("Database tables created")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)