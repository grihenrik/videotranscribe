from datetime import datetime
from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from sqlalchemy import UniqueConstraint, func

# Get db instance from main module to avoid circular imports
def get_db():
    from main import db
    return db

db = get_db()

# User model
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(255), primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=True)
    first_name = db.Column(db.String(255), nullable=True)
    last_name = db.Column(db.String(255), nullable=True)
    profile_image_url = db.Column(db.String(255), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # User settings
    notification_email = db.Column(db.Boolean, default=True)
    notification_site = db.Column(db.Boolean, default=True)
    
    # User transcriptions relationship
    transcriptions = db.relationship('Transcription', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.email}>'

# OAuth model for authentication
class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String(255), db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String(255), nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

# OAuth Provider Settings model
class OAuthProviderSettings(db.Model):
    """Model for storing OAuth provider settings"""
    __tablename__ = 'oauth_provider_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    provider_name = db.Column(db.String(50), unique=True, nullable=False)
    is_enabled = db.Column(db.Boolean, default=False)
    client_id = db.Column(db.String(255))
    client_secret = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<OAuthProviderSettings {self.provider_name}>'

# Transcription model to track user usage
class Transcription(db.Model):
    __tablename__ = 'transcriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), db.ForeignKey('users.id'), nullable=True)
    video_id = db.Column(db.String(255), nullable=False)
    video_title = db.Column(db.String(255))
    url = db.Column(db.String(255))
    mode = db.Column(db.String(50))  # captions, whisper, auto
    language = db.Column(db.String(10))
    duration = db.Column(db.Integer)  # video duration in seconds
    status = db.Column(db.String(50))  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.now)
    completed_at = db.Column(db.DateTime, nullable=True)
    batch_id = db.Column(db.String(255), nullable=True)  # For batch processing
    
    def __repr__(self):
        return f'<Transcription {self.id} - {self.video_title}>'

# User Notification model
class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), db.ForeignKey('users.id'))
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Notification {self.id} for {self.user_id}>'

# Analytics for admin dashboard
class DailyStats(db.Model):
    __tablename__ = 'daily_stats'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    total_transcriptions = db.Column(db.Integer, default=0)
    total_duration = db.Column(db.Integer, default=0)  # total seconds processed
    whisper_count = db.Column(db.Integer, default=0)
    captions_count = db.Column(db.Integer, default=0)
    auto_count = db.Column(db.Integer, default=0)
    batch_count = db.Column(db.Integer, default=0)
    playlist_count = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Float, default=0.0)  # percentage of successful transcriptions
    
    __table_args__ = (UniqueConstraint('date', name='uq_daily_stats_date'),)
    
    def __repr__(self):
        return f'<DailyStats {self.date}>'