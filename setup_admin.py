"""
Simple script to create an admin user directly from the command line.
This is useful for initial setup of the application.
"""
import os
import sys
import uuid
from datetime import datetime

# Check if email is provided
if len(sys.argv) != 2:
    print("Usage: python setup_admin.py admin@example.com")
    sys.exit(1)

admin_email = sys.argv[1]

# Import the app context to access the database
from app import app, db
from models import User, OAuthProviderSettings

with app.app_context():
    # Check if user already exists
    existing_user = User.query.filter_by(email=admin_email).first()
    
    if existing_user:
        # Make the user an admin if they're not already
        if not existing_user.is_admin:
            existing_user.is_admin = True
            db.session.commit()
            print(f"User {admin_email} upgraded to admin status.")
        else:
            print(f"User {admin_email} is already an admin.")
    else:
        # Create a new admin user
        admin_id = f"manual:{uuid.uuid4()}"
        admin_user = User(
            id=admin_id,
            email=admin_email,
            first_name="Admin",
            last_name="User",
            is_admin=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.session.add(admin_user)
        db.session.commit()
        print(f"Created new admin user: {admin_email}")
    
    # Set up default OAuth providers if they don't exist
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
    
    print("\nSetup complete!")
    print("You can now log in with this email through any enabled OAuth provider")
    print("After logging in, visit /admin to access the admin panel")