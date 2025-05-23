import os
import datetime
from datetime import timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from sqlalchemy import func, desc, and_

from app import db
from models import User, Transcription, DailyStats, OAuthProviderSettings
from auth import admin_required

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard page"""
    days = request.args.get('days', 7, type=int)
    
    # Date range for filtering
    end_date = datetime.datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    # Add transcription count to each user
    for user in recent_users:
        user.transcription_count = Transcription.query.filter_by(user_id=user.id).count()
    
    # Get recent transcriptions
    recent_transcriptions = Transcription.query.order_by(
        Transcription.created_at.desc()
    ).limit(5).all()
    
    # Get stats for the dashboard
    total_transcriptions = Transcription.query.count()
    total_users = User.query.count()
    completed_transcriptions = Transcription.query.filter_by(status='completed').count()
    success_rate = int((completed_transcriptions / total_transcriptions * 100) if total_transcriptions > 0 else 0)
    
    # Calculate growth rates
    prev_period_start = start_date - timedelta(days=days)
    prev_period_transcriptions = Transcription.query.filter(
        Transcription.created_at.between(prev_period_start, start_date)
    ).count()
    
    current_period_transcriptions = Transcription.query.filter(
        Transcription.created_at.between(start_date, end_date)
    ).count()
    
    transcription_growth = int(
        ((current_period_transcriptions - prev_period_transcriptions) / max(1, prev_period_transcriptions)) * 100
    )
    
    prev_period_users = User.query.filter(
        User.created_at.between(prev_period_start, start_date)
    ).count()
    
    current_period_users = User.query.filter(
        User.created_at.between(start_date, end_date)
    ).count()
    
    user_growth = int(
        ((current_period_users - prev_period_users) / max(1, prev_period_users)) * 100
    )
    
    # Get processing time data (placeholder for now)
    avg_processing_time = "1:24"
    processing_time_improvement = 15
    
    # Get system performance metrics
    api_usage = 65
    system_load = 42
    queue_size = 3
    queue_size_percent = int((queue_size / 10) * 100)  # Assuming max queue size is 10
    
    metrics = {
        'total_transcriptions': total_transcriptions,
        'total_users': total_users,
        'success_rate': success_rate,
        'avg_processing_time': avg_processing_time,
        'transcription_growth': transcription_growth,
        'user_growth': user_growth,
        'processing_time_improvement': processing_time_improvement,
        'api_usage': api_usage,
        'system_load': system_load,
        'queue_size': queue_size,
        'queue_size_percent': queue_size_percent
    }
    
    # Get chart data
    date_labels = []
    transcription_counts = []
    success_rates = []
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime('%b %d')
        date_labels.append(date_str)
        
        # Count transcriptions for this day
        day_transcriptions = Transcription.query.filter(
            func.date(Transcription.created_at) == current_date.date()
        ).count()
        
        transcription_counts.append(day_transcriptions)
        
        # Calculate success rate for this day
        day_completed = Transcription.query.filter(
            func.date(Transcription.created_at) == current_date.date(),
            Transcription.status == 'completed'
        ).count()
        
        day_success_rate = int((day_completed / max(1, day_transcriptions)) * 100)
        success_rates.append(day_success_rate)
        
        current_date += timedelta(days=1)
    
    # Count transcription methods
    whisper_count = Transcription.query.filter_by(mode='whisper').count()
    captions_count = Transcription.query.filter_by(mode='captions').count()
    auto_count = Transcription.query.filter_by(mode='auto').count()
    
    chart_data = {
        'dates': date_labels,
        'transcription_counts': transcription_counts,
        'success_rates': success_rates,
        'whisper_count': whisper_count,
        'captions_count': captions_count,
        'auto_count': auto_count
    }
    
    return render_template(
        'admin_dashboard.html',
        metrics=metrics,
        recent_users=recent_users,
        recent_transcriptions=recent_transcriptions,
        chart_data=chart_data
    )

@admin_bp.route('/oauth-settings')
@login_required
@admin_required
def oauth_settings():
    """Admin OAuth settings page"""
    # Get current OAuth provider settings
    google_settings = OAuthProviderSettings.query.filter_by(provider_name='google').first()
    twitter_settings = OAuthProviderSettings.query.filter_by(provider_name='twitter').first()
    discord_settings = OAuthProviderSettings.query.filter_by(provider_name='discord').first()
    
    # Create default settings if they don't exist
    if not google_settings:
        google_settings = OAuthProviderSettings(
            provider_name='google',
            is_enabled=False,
            client_id=os.environ.get('GOOGLE_CLIENT_ID', ''),
            client_secret=os.environ.get('GOOGLE_CLIENT_SECRET', '')
        )
        db.session.add(google_settings)
        
    if not twitter_settings:
        twitter_settings = OAuthProviderSettings(
            provider_name='twitter',
            is_enabled=False,
            client_id=os.environ.get('TWITTER_CLIENT_ID', ''),
            client_secret=os.environ.get('TWITTER_CLIENT_SECRET', '')
        )
        db.session.add(twitter_settings)
        
    if not discord_settings:
        discord_settings = OAuthProviderSettings(
            provider_name='discord',
            is_enabled=False,
            client_id=os.environ.get('DISCORD_CLIENT_ID', ''),
            client_secret=os.environ.get('DISCORD_CLIENT_SECRET', '')
        )
        db.session.add(discord_settings)
        
    db.session.commit()
    
    # Get the callback domain (for displaying in UI)
    callback_domain = request.host_url.rstrip('/')
    if callback_domain.startswith('http:'):
        callback_domain = callback_domain.replace('http:', 'https:')
    
    return render_template(
        'admin_oauth.html',
        google_enabled=google_settings.is_enabled,
        google_client_id=google_settings.client_id,
        google_client_secret='●●●●●●●●●●●●' if google_settings.client_secret else '',
        twitter_enabled=twitter_settings.is_enabled,
        twitter_client_id=twitter_settings.client_id,
        twitter_client_secret='●●●●●●●●●●●●' if twitter_settings.client_secret else '',
        discord_enabled=discord_settings.is_enabled,
        discord_client_id=discord_settings.client_id,
        discord_client_secret='●●●●●●●●●●●●' if discord_settings.client_secret else '',
        callback_domain=callback_domain
    )

@admin_bp.route('/update-oauth-settings', methods=['POST'])
@login_required
@admin_required
def update_oauth_settings():
    """Update OAuth provider settings"""
    provider = request.form.get('provider')
    enabled = 'enabled' in request.form
    client_id = request.form.get('client_id', '')
    client_secret = request.form.get('client_secret', '')
    
    if not provider:
        flash('Provider name is required', 'danger')
        return redirect(url_for('admin.oauth_settings'))
    
    # Get the provider settings
    provider_settings = OAuthProviderSettings.query.filter_by(provider_name=provider).first()
    
    if not provider_settings:
        provider_settings = OAuthProviderSettings(provider_name=provider)
        db.session.add(provider_settings)
    
    # Update the settings
    provider_settings.is_enabled = enabled
    
    # Only update client ID if provided
    if client_id:
        provider_settings.client_id = client_id
    
    # Only update client secret if provided and not masked
    if client_secret and not client_secret.startswith('●'):
        provider_settings.client_secret = client_secret
    
    db.session.commit()
    
    # Also update environment variables for immediate effect
    if provider == 'google':
        os.environ['GOOGLE_CLIENT_ID'] = client_id or os.environ.get('GOOGLE_CLIENT_ID', '')
        if client_secret and not client_secret.startswith('●'):
            os.environ['GOOGLE_CLIENT_SECRET'] = client_secret
    elif provider == 'twitter':
        os.environ['TWITTER_CLIENT_ID'] = client_id or os.environ.get('TWITTER_CLIENT_ID', '')
        if client_secret and not client_secret.startswith('●'):
            os.environ['TWITTER_CLIENT_SECRET'] = client_secret
    elif provider == 'discord':
        os.environ['DISCORD_CLIENT_ID'] = client_id or os.environ.get('DISCORD_CLIENT_ID', '')
        if client_secret and not client_secret.startswith('●'):
            os.environ['DISCORD_CLIENT_SECRET'] = client_secret
    
    # Reload OAuth providers in auth module
    from auth import register_oauth_providers
    register_oauth_providers()
    
    flash(f'{provider.capitalize()} OAuth settings updated successfully', 'success')
    return redirect(url_for('admin.oauth_settings'))

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """Admin users management page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_query = request.args.get('search', '')
    
    # Base query
    query = User.query
    
    # Apply search filter
    if search_query:
        query = query.filter(
            (User.email.ilike(f'%{search_query}%')) |
            (User.first_name.ilike(f'%{search_query}%')) |
            (User.last_name.ilike(f'%{search_query}%'))
        )
    
    # Order by most recent first
    query = query.order_by(User.created_at.desc())
    
    # Paginate results
    paginated_users = query.paginate(page=page, per_page=per_page)
    
    # Add transcription count to each user
    for user in paginated_users.items:
        user.transcription_count = Transcription.query.filter_by(user_id=user.id).count()
    
    pagination = {
        'page': page,
        'pages': paginated_users.pages
    }
    
    return render_template(
        'admin_users.html',
        users=paginated_users.items,
        pagination=pagination,
        search_query=search_query
    )

@admin_bp.route('/toggle-admin/<user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    """Toggle admin status for a user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent removing admin status from yourself
    if user.id == current_user.id:
        flash('You cannot change your own admin status', 'danger')
        return redirect(url_for('admin.users'))
    
    # Toggle admin status
    user.is_admin = not user.is_admin
    db.session.commit()
    
    action = 'granted' if user.is_admin else 'revoked'
    flash(f'Admin privileges {action} for {user.email}', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/transcriptions')
@login_required
@admin_required
def transcriptions():
    """Admin transcriptions management page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status_filter = request.args.get('status', 'all')
    mode_filter = request.args.get('mode', 'all')
    search_query = request.args.get('search', '')
    
    # Base query
    query = Transcription.query
    
    # Apply filters
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if mode_filter != 'all':
        query = query.filter_by(mode=mode_filter)
    
    if search_query:
        query = query.filter(Transcription.video_title.ilike(f'%{search_query}%'))
    
    # Order by most recent first
    query = query.order_by(Transcription.created_at.desc())
    
    # Paginate results
    paginated_transcriptions = query.paginate(page=page, per_page=per_page)
    
    pagination = {
        'page': page,
        'pages': paginated_transcriptions.pages
    }
    
    # Get counts for filters
    status_counts = {
        'all': Transcription.query.count(),
        'completed': Transcription.query.filter_by(status='completed').count(),
        'pending': Transcription.query.filter_by(status='pending').count(),
        'failed': Transcription.query.filter_by(status='failed').count()
    }
    
    mode_counts = {
        'all': Transcription.query.count(),
        'whisper': Transcription.query.filter_by(mode='whisper').count(),
        'captions': Transcription.query.filter_by(mode='captions').count(),
        'auto': Transcription.query.filter_by(mode='auto').count()
    }
    
    return render_template(
        'admin_transcriptions.html',
        transcriptions=paginated_transcriptions.items,
        pagination=pagination,
        status_filter=status_filter,
        mode_filter=mode_filter,
        search_query=search_query,
        status_counts=status_counts,
        mode_counts=mode_counts
    )

@admin_bp.route('/delete-transcription/<transcription_id>', methods=['POST'])
@login_required
@admin_required
def delete_transcription(transcription_id):
    """Delete a transcription (admin only)"""
    transcription = Transcription.query.get_or_404(transcription_id)
    
    db.session.delete(transcription)
    db.session.commit()
    
    flash('Transcription deleted successfully', 'success')
    return redirect(url_for('admin.transcriptions'))

@admin_bp.route('/update-daily-stats', methods=['POST'])
@login_required
@admin_required
def update_daily_stats():
    """Manual trigger to update daily statistics"""
    # Update stats for current day
    today = datetime.datetime.now().date()
    
    # Check if we already have stats for today
    daily_stats = DailyStats.query.filter_by(date=today).first()
    
    if not daily_stats:
        daily_stats = DailyStats(date=today)
        db.session.add(daily_stats)
    
    # Update the stats
    today_transcriptions = Transcription.query.filter(
        func.date(Transcription.created_at) == today
    )
    
    daily_stats.total_transcriptions = today_transcriptions.count()
    
    # Count by mode
    daily_stats.whisper_count = today_transcriptions.filter_by(mode='whisper').count()
    daily_stats.captions_count = today_transcriptions.filter_by(mode='captions').count()
    daily_stats.auto_count = today_transcriptions.filter_by(mode='auto').count()
    
    # Count batch and playlist
    daily_stats.batch_count = today_transcriptions.filter(Transcription.batch_id.isnot(None)).count()
    
    # Calculate total duration
    daily_stats.total_duration = today_transcriptions.with_entities(
        func.sum(Transcription.duration)
    ).scalar() or 0
    
    # Calculate success rate
    completed_count = today_transcriptions.filter_by(status='completed').count()
    daily_stats.success_rate = (completed_count / daily_stats.total_transcriptions * 100) if daily_stats.total_transcriptions > 0 else 0
    
    db.session.commit()
    
    flash('Daily statistics updated successfully', 'success')
    return redirect(url_for('admin.dashboard'))