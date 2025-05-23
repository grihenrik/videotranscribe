"""
Script to create an initial admin user in the database.
Run this script directly to create an admin user:
    python create_admin.py
"""
import os
import sys
import uuid
from datetime import datetime

# Make sure environment has all required variables
REQUIRED_ENV_VARS = ["DATABASE_URL", "SESSION_SECRET"]
missing_vars = [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]
if missing_vars:
    print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please set these variables and try again.")
    sys.exit(1)

# Import from app context to access database
from app import app, db
from models import User, OAuth

def create_admin_user(email, provider="manual", admin_id=None):
    """
    Create an admin user in the database.
    
    Args:
        email: Email address for the admin user
        provider: Authentication provider (default: manual)
        admin_id: Optional specific ID to use
    
    Returns:
        The created user object
    """
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            if existing_user.is_admin:
                print(f"Admin user {email} already exists.")
                return existing_user
            else:
                # Upgrade to admin
                existing_user.is_admin = True
                db.session.commit()
                print(f"Upgraded user {email} to admin status.")
                return existing_user
        
        # Create new admin user
        user_id = admin_id or f"{provider}:{uuid.uuid4()}"
        user = User(
            id=user_id,
            email=email,
            first_name="Admin",
            last_name="User",
            is_admin=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.session.add(user)
        db.session.commit()
        print(f"Created new admin user: {email}")
        return user

def setup_oauth_providers():
    """Initialize OAuth provider settings in the database"""
    from models import OAuthProviderSettings
    
    with app.app_context():
        providers = [
            {
                "name": "google",
                "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
                "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", "")
            },
            {
                "name": "twitter", 
                "client_id": os.environ.get("TWITTER_CLIENT_ID", ""),
                "client_secret": os.environ.get("TWITTER_CLIENT_SECRET", "")
            },
            {
                "name": "discord",
                "client_id": os.environ.get("DISCORD_CLIENT_ID", ""),
                "client_secret": os.environ.get("DISCORD_CLIENT_SECRET", "")
            }
        ]
        
        for provider in providers:
            existing = OAuthProviderSettings.query.filter_by(provider_name=provider["name"]).first()
            if not existing:
                # Create new provider settings
                settings = OAuthProviderSettings(
                    provider_name=provider["name"],
                    is_enabled=bool(provider["client_id"] and provider["client_secret"]),
                    client_id=provider["client_id"],
                    client_secret=provider["client_secret"]
                )
                db.session.add(settings)
                print(f"Created settings for {provider['name']} OAuth provider")
        
        db.session.commit()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        admin_email = sys.argv[1]
    else:
        admin_email = input("Enter email for admin user: ")
    
    # Create admin user
    create_admin_user(admin_email)
    
    # Setup OAuth providers
    setup_oauth_providers()
    
    print("\nSetup complete! You can now log in with your OAuth provider and manage settings.")
    print("Note: Make sure the admin email matches your OAuth provider email.")