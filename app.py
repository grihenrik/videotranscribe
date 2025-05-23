import os
import logging
import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, session, Response
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define the SQLAlchemy base class
class Base(DeclarativeBase):
    pass

# Initialize the Flask app
app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # For proper URL generation behind proxies

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Initialize SQLAlchemy
db = SQLAlchemy(app, model_class=Base)

# Create tables within the app context
with app.app_context():
    # Import models (after db is defined)
    import models
    db.create_all()
    logger.info("Database tables created")

# Initialize LoginManager
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(user_id)

# Register the timeago template filter
from filters import timeago

@app.template_filter('timeago')
def timeago_filter(dt):
    return timeago(dt)

# Set up context processors for template globals
@app.context_processor
def inject_globals():
    return {
        'current_year': datetime.datetime.now().year,
        'unread_notifications_count': get_unread_notifications_count()
    }

def get_unread_notifications_count():
    """Get count of unread notifications for the current user"""
    if current_user.is_authenticated:
        return models.Notification.query.filter_by(
            user_id=current_user.id, 
            read=False
        ).count()
    return 0

# Import and register authentication blueprint
import auth