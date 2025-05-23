import os
import uuid
import jwt
from functools import wraps
from urllib.parse import urlencode

from flask import g, session, redirect, request, render_template, url_for, flash, jsonify, Blueprint
from flask_dance.consumer import OAuth2ConsumerBlueprint, oauth_authorized, oauth_error
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from flask_login import LoginManager, login_user, logout_user, current_user
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from sqlalchemy.exc import NoResultFound

# Import from the global app and db objects
from app import app, db
from models import User, OAuth

# Create auth blueprint
auth_bp = Blueprint('auth', __name__, template_folder='templates')

# Create a LoginManager instance
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

class UserSessionStorage:
    """Custom storage for OAuth tokens that links them to user sessions"""
    def __init__(self, model, session_key):
        self.model = model
        self.session_key = session_key

    def get(self, blueprint):
        try:
            token = db.session.query(self.model).filter_by(
                user_id=current_user.get_id(),
                browser_session_key=session.get(self.session_key),
                provider=blueprint.name,
            ).one().token
        except NoResultFound:
            token = None
        return token

    def set(self, blueprint, token):
        if current_user.is_authenticated:
            db.session.query(self.model).filter_by(
                user_id=current_user.get_id(),
                browser_session_key=session.get(self.session_key),
                provider=blueprint.name,
            ).delete()
            new_model = self.model()
            new_model.user_id = current_user.get_id()
            new_model.browser_session_key = session.get(self.session_key)
            new_model.provider = blueprint.name
            new_model.token = token
            db.session.add(new_model)
            db.session.commit()

    def delete(self, blueprint):
        if current_user.is_authenticated:
            db.session.query(self.model).filter_by(
                user_id=current_user.get_id(),
                browser_session_key=session.get(self.session_key),
                provider=blueprint.name
            ).delete()
            db.session.commit()

# Google OAuth setup
def setup_google_oauth():
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        app.logger.warning("Google OAuth not configured: missing credentials")
        return None
    
    storage = UserSessionStorage(OAuth, '_browser_session_key')
    
    google_bp = OAuth2ConsumerBlueprint(
        "google",
        __name__,
        client_id=client_id,
        client_secret=client_secret,
        scope=["openid", "email", "profile"],
        base_url="https://www.googleapis.com/oauth2/v1/",
        authorization_url="https://accounts.google.com/o/oauth2/auth",
        token_url="https://accounts.google.com/o/oauth2/token",
        redirect_url="https://thetranscriptiontool.replit.app/auth/google/authorized",
        redirect_to="auth.google_authorized",
        storage=storage,
    )
    
    return google_bp

# Twitter OAuth setup
def setup_twitter_oauth():
    client_id = os.environ.get("TWITTER_CLIENT_ID")
    client_secret = os.environ.get("TWITTER_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        app.logger.warning("Twitter OAuth not configured: missing credentials")
        return None
    
    storage = UserSessionStorage(OAuth, '_browser_session_key')
    
    twitter_bp = OAuth2ConsumerBlueprint(
        "twitter",
        __name__,
        client_id=client_id,
        client_secret=client_secret,
        scope=["tweet.read", "users.read", "offline.access"],
        base_url="https://api.twitter.com/2/",
        authorization_url="https://twitter.com/i/oauth2/authorize",
        token_url="https://api.twitter.com/2/oauth2/token",
        redirect_url="https://thetranscriptiontool.replit.app/auth/twitter/authorized",
        redirect_to="auth.twitter_authorized",
        storage=storage,
    )
    
    return twitter_bp

# Discord OAuth setup
def setup_discord_oauth():
    client_id = os.environ.get("DISCORD_CLIENT_ID")
    client_secret = os.environ.get("DISCORD_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        app.logger.warning("Discord OAuth not configured: missing credentials")
        return None
    
    storage = UserSessionStorage(OAuth, '_browser_session_key')
    
    discord_bp = OAuth2ConsumerBlueprint(
        "discord",
        __name__,
        client_id=client_id,
        client_secret=client_secret,
        scope=["identify", "email"],
        base_url="https://discord.com/api/",
        authorization_url="https://discord.com/api/oauth2/authorize",
        token_url="https://discord.com/api/oauth2/token",
        redirect_url="https://thetranscriptiontool.replit.app/auth/discord/authorized",
        redirect_to="auth.discord_authorized",
        storage=storage,
    )
    
    return discord_bp

# Register OAuth providers
def register_oauth_providers():
    # Set up session key for browser
    @app.before_request
    def set_browser_session_key():
        if '_browser_session_key' not in session:
            session['_browser_session_key'] = uuid.uuid4().hex
        session.modified = True
    
    # Register available providers
    providers = []
    
    google_bp = setup_google_oauth()
    if google_bp:
        app.register_blueprint(google_bp, url_prefix="/login")
        providers.append("google")
    
    twitter_bp = setup_twitter_oauth()
    if twitter_bp:
        app.register_blueprint(twitter_bp, url_prefix="/login")
        providers.append("twitter")
    
    discord_bp = setup_discord_oauth()
    if discord_bp:
        app.register_blueprint(discord_bp, url_prefix="/login")
        providers.append("discord")
    
    app.config['OAUTH_PROVIDERS'] = providers
    
    return providers

# Route for login page
@auth_bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    providers = app.config.get('OAUTH_PROVIDERS', [])
    return render_template('login.html', providers=providers)

# OAuth callback routes
@auth_bp.route('/google/authorized')
def google_authorized():
    # This is the URL that Google will redirect to after authentication
    if current_user.is_authenticated:
        flash('Successfully signed in with Google!', 'success')
        next_url = session.pop('next_url', None) or url_for('index')
        return redirect(next_url)
    else:
        flash('Google login failed. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

@auth_bp.route('/twitter/authorized')
def twitter_authorized():
    # This is the URL that Twitter will redirect to after authentication
    if current_user.is_authenticated:
        flash('Successfully signed in with Twitter!', 'success')
        next_url = session.pop('next_url', None) or url_for('index')
        return redirect(next_url)
    else:
        flash('Twitter login failed. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

@auth_bp.route('/discord/authorized')
def discord_authorized():
    # This is the URL that Discord will redirect to after authentication
    if current_user.is_authenticated:
        flash('Successfully signed in with Discord!', 'success')
        next_url = session.pop('next_url', None) or url_for('index')
        return redirect(next_url)
    else:
        flash('Discord login failed. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

# Generic callback after OAuth login
@auth_bp.route('/oauth-callback')
def oauth_callback():
    # This route will be hit after a successful OAuth login
    # The user will be already logged in by the oauth_authorized handler
    if current_user.is_authenticated:
        flash('Successfully logged in!', 'success')
        return redirect(url_for('index'))
    else:
        flash('Login failed. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

# Route for logout
@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Decorator for admin-only routes
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need to be an admin to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator for login-required routes with next URL support
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # Store the current URL for redirection after login
            session['next_url'] = request.url
            flash('You need to be logged in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Register the OAuth authorized handler
@oauth_authorized.connect
def oauth_authorized_handler(blueprint, token):
    # Get user info from the appropriate provider
    if blueprint.name == 'google':
        resp = blueprint.session.get("userinfo")
        user_info = resp.json()
        
        # Extract user details
        user_id = f"google:{user_info['id']}"
        email = user_info.get('email')
        first_name = user_info.get('given_name')
        last_name = user_info.get('family_name')
        profile_image = user_info.get('picture')
        
    elif blueprint.name == 'twitter':
        resp = blueprint.session.get("users/me")
        user_info = resp.json()
        
        # Extract user details
        user_id = f"twitter:{user_info['data']['id']}"
        email = user_info['data'].get('email')
        name_parts = user_info['data'].get('name', '').split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        profile_image = user_info['data'].get('profile_image_url')
        
    elif blueprint.name == 'discord':
        resp = blueprint.session.get("users/@me")
        user_info = resp.json()
        
        # Extract user details
        user_id = f"discord:{user_info['id']}"
        email = user_info.get('email')
        first_name = user_info.get('username')
        last_name = ''  # Discord doesn't have last name
        # Discord avatar URL construction
        if user_info.get('avatar'):
            cdn_fmt = 'https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png'
            profile_image = cdn_fmt.format(user_id=user_info['id'], avatar=user_info['avatar'])
        else:
            profile_image = None
    else:
        # Unsupported provider
        flash(f"Login with {blueprint.name} is not fully supported yet.", "warning")
        return False
    
    # Find or create the user
    try:
        # Look for existing user
        user = User.query.filter_by(id=user_id).one()
    except NoResultFound:
        # Create a new user
        user = User(
            id=user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            profile_image_url=profile_image
        )
        db.session.add(user)
        db.session.commit()
    
    # Log in the user
    login_user(user)
    
    # Store the OAuth token
    blueprint.storage.set(blueprint, token)
    
    # Check if we need to redirect to a specific page
    next_url = session.pop('next_url', None) or url_for('index')
    
    flash(f"Successfully signed in with {blueprint.name}!", "success")
    return redirect(next_url)

# Register the OAuth error handler
@oauth_error.connect
def oauth_error_handler(blueprint, error, error_description=None, error_uri=None):
    app.logger.error(f"OAuth error from {blueprint.name}: {error}")
    flash(f"Authentication error: {error_description or error}", "danger")
    return redirect(url_for('auth.login'))

# Register the blueprint with the app
app.register_blueprint(auth_bp, url_prefix='/auth')

# Initialize OAuth providers
register_oauth_providers()