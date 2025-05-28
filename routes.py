import os
import time
import uuid
import datetime
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_

from flask import render_template, redirect, url_for, request, jsonify, flash, Response, send_file, session
from flask_login import current_user, login_required

from flask_app import app, db
from models import User, Transcription, Notification, DailyStats
from auth import admin_required

# Utility functions
def format_duration(seconds):
    """Format seconds into human-readable duration (HH:MM:SS)"""
    if not seconds:
        return "--:--"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"

def get_unread_notifications_count():
    """Get count of unread notifications for the current user"""
    if current_user.is_authenticated:
        return Notification.query.filter_by(
            user_id=current_user.id, 
            read=False
        ).count()
    return 0

# Context processor to add data to all templates
@app.context_processor
def inject_global_data():
    return {
        'current_year': datetime.now().year,
        'unread_notifications_count': get_unread_notifications_count(),
        'available_providers': app.config.get('OAUTH_PROVIDERS', [])
    }

# Custom decorator to track user activity
def track_activity(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Track user activity if authenticated
        if current_user.is_authenticated:
            # Update user's last activity timestamp
            # We could add a 'last_active' field to the User model
            pass
        return f(*args, **kwargs)
    return decorated_function

# === Main Application Routes ===

@app.route('/')
@track_activity
def index():
    """Home page with single video transcription form"""
    return render_template('index.html')

@app.route('/batch')
@track_activity
def batch():
    """Batch processing page"""
    return render_template('batch.html')

@app.route('/playlist')
@track_activity
def playlist():
    """Playlist processing page"""
    return render_template('playlist.html')

# === User Routes ===

@app.route('/dashboard')
@login_required
@track_activity
def dashboard():
    """Personalized user dashboard with activity insights"""
    user_transcriptions = Transcription.query.filter_by(user_id=current_user.id)
    
    # Basic statistics
    total_transcriptions = user_transcriptions.count()
    completed_count = user_transcriptions.filter_by(status='completed').count()
    failed_count = user_transcriptions.filter_by(status='failed').count()
    pending_count = user_transcriptions.filter_by(status='pending').count()
    
    # Success rate
    success_rate = int((completed_count / total_transcriptions * 100) if total_transcriptions > 0 else 0)
    
    # Total duration processed
    total_duration = user_transcriptions.filter_by(status='completed').with_entities(func.sum(Transcription.duration)).scalar() or 0
    total_duration_formatted = format_duration(total_duration)
    
    # Recent activity (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    recent_transcriptions = user_transcriptions.filter(Transcription.created_at >= week_ago).count()
    
    # Mode usage statistics
    whisper_count = user_transcriptions.filter_by(mode='whisper').count()
    captions_count = user_transcriptions.filter_by(mode='captions').count()
    auto_count = user_transcriptions.filter_by(mode='auto').count()
    
    # Monthly activity (last 30 days by day)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    daily_activity = []
    for i in range(30):
        day = datetime.now() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        daily_count = user_transcriptions.filter(
            and_(Transcription.created_at >= day_start, Transcription.created_at < day_end)
        ).count()
        
        daily_activity.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'count': daily_count
        })
    
    daily_activity.reverse()  # Show oldest to newest
    
    # Recent transcriptions for quick access
    recent_files = user_transcriptions.order_by(desc(Transcription.created_at)).limit(5).all()
    
    # Language usage statistics
    language_stats = db.session.query(
        Transcription.language, 
        func.count(Transcription.id).label('count')
    ).filter_by(user_id=current_user.id).group_by(Transcription.language).all()
    
    # Calculate average processing time for completed transcriptions
    completed_transcriptions = user_transcriptions.filter_by(status='completed').all()
    if completed_transcriptions:
        processing_times = []
        for trans in completed_transcriptions:
            if trans.completed_at and trans.created_at:
                processing_time = (trans.completed_at - trans.created_at).total_seconds()
                processing_times.append(processing_time)
        
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        avg_processing_time_formatted = format_duration(int(avg_processing_time))
    else:
        avg_processing_time_formatted = "--:--"
    
    dashboard_data = {
        'total_transcriptions': total_transcriptions,
        'completed_count': completed_count,
        'failed_count': failed_count,
        'pending_count': pending_count,
        'success_rate': success_rate,
        'total_duration_formatted': total_duration_formatted,
        'recent_transcriptions': recent_transcriptions,
        'whisper_count': whisper_count,
        'captions_count': captions_count,
        'auto_count': auto_count,
        'daily_activity': daily_activity,
        'recent_files': recent_files,
        'language_stats': language_stats,
        'avg_processing_time': avg_processing_time_formatted
    }
    
    return render_template('dashboard.html', **dashboard_data)

@app.route('/settings')
@login_required
@track_activity
def settings():
    """User settings page"""
    # Calculate user statistics
    user_transcriptions = Transcription.query.filter_by(user_id=current_user.id)
    total_transcriptions = user_transcriptions.count()
    
    # Calculate success rate
    completed_count = user_transcriptions.filter_by(status='completed').count()
    success_rate = int((completed_count / total_transcriptions * 100) if total_transcriptions > 0 else 0)
    
    # Calculate total duration
    total_duration = user_transcriptions.with_entities(func.sum(Transcription.duration)).scalar() or 0
    total_duration_formatted = format_duration(total_duration)
    
    stats = {
        'total_transcriptions': total_transcriptions,
        'total_duration_formatted': total_duration_formatted,
        'success_rate': success_rate
    }
    
    return render_template('settings.html', stats=stats)

@app.route('/update-notification-settings', methods=['POST'])
@login_required
def update_notification_settings():
    """Update user notification settings"""
    notification_email = 'notification_email' in request.form
    notification_site = 'notification_site' in request.form
    
    current_user.notification_email = notification_email
    current_user.notification_site = notification_site
    db.session.commit()
    
    flash('Notification settings updated successfully', 'success')
    return redirect(url_for('settings'))

@app.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account and all associated data"""
    if 'confirm_delete' in request.form:
        # Delete user's notifications
        Notification.query.filter_by(user_id=current_user.id).delete()
        
        # Remove user ID from transcriptions but keep the transcriptions
        Transcription.query.filter_by(user_id=current_user.id).update({Transcription.user_id: None})
        
        # Delete OAuth tokens
        OAuth.query.filter_by(user_id=current_user.id).delete()
        
        # Delete the user
        user_id = current_user.id
        db.session.delete(current_user._get_current_object())
        db.session.commit()
        
        flash('Your account has been deleted successfully', 'success')
        return redirect(url_for('index'))
    
    flash('Please confirm the account deletion', 'danger')
    return redirect(url_for('settings'))

@app.route('/history')
@login_required
@track_activity
def history():
    """User transcription history page"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Filter parameters
    status_filter = request.args.get('status', 'all')
    type_filter = request.args.get('type', 'all')
    search_query = request.args.get('search', '')
    
    # Base query
    query = Transcription.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if type_filter == 'batch':
        query = query.filter(Transcription.batch_id.isnot(None))
    elif type_filter == 'single':
        query = query.filter(Transcription.batch_id.is_(None))
    
    if search_query:
        query = query.filter(Transcription.video_title.ilike(f'%{search_query}%'))
    
    # Order by most recent first
    query = query.order_by(Transcription.created_at.desc())
    
    # Paginate results
    paginated_transcriptions = query.paginate(page=page, per_page=per_page)
    
    # Calculate statistics
    total_count = query.count()
    total_duration = query.with_entities(func.sum(Transcription.duration)).scalar() or 0
    success_count = query.filter_by(status='completed').count()
    success_rate = int((success_count / total_count * 100) if total_count > 0 else 0)
    
    # Get favorite method
    method_counts = db.session.query(
        Transcription.mode, 
        func.count(Transcription.id).label('count')
    ).filter_by(
        user_id=current_user.id
    ).group_by(
        Transcription.mode
    ).order_by(
        desc('count')
    ).first()
    
    favorite_method = method_counts[0].capitalize() if method_counts else "N/A"
    
    stats = {
        'total_count': total_count,
        'total_duration': format_duration(total_duration),
        'success_rate': success_rate,
        'favorite_method': favorite_method
    }
    
    pagination = {
        'page': page,
        'pages': paginated_transcriptions.pages
    }
    
    return render_template(
        'history.html', 
        transcriptions=paginated_transcriptions.items,
        pagination=pagination,
        stats=stats
    )

@app.route('/notifications')
@login_required
@track_activity
def notifications():
    """User notifications page"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Notification.created_at.desc()
    ).paginate(page=page, per_page=per_page)
    
    pagination = {
        'page': page,
        'pages': notifications.pages
    }
    
    return render_template(
        'notifications.html', 
        notifications=notifications.items,
        pagination=pagination
    )

@app.route('/mark-notification-read/<int:notification_id>')
@login_required
def mark_notification_read(notification_id):
    """Mark a single notification as read"""
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=current_user.id
    ).first_or_404()
    
    notification.read = True
    db.session.commit()
    
    flash('Notification marked as read', 'success')
    return redirect(url_for('notifications'))

@app.route('/mark-all-read')
@login_required
def mark_all_read():
    """Mark all notifications as read"""
    Notification.query.filter_by(
        user_id=current_user.id,
        read=False
    ).update({Notification.read: True})
    
    db.session.commit()
    
    flash('All notifications marked as read', 'success')
    return redirect(url_for('notifications'))

@app.route('/delete-notification/<int:notification_id>')
@login_required
def delete_notification(notification_id):
    """Delete a notification"""
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=current_user.id
    ).first_or_404()
    
    db.session.delete(notification)
    db.session.commit()
    
    flash('Notification deleted', 'success')
    return redirect(url_for('notifications'))

@app.route('/delete-transcription', methods=['POST'])
@login_required
def delete_transcription():
    """Delete a transcription"""
    transcription_id = request.form.get('transcription_id')
    
    transcription = Transcription.query.filter_by(
        id=transcription_id,
        user_id=current_user.id
    ).first_or_404()
    
    db.session.delete(transcription)
    db.session.commit()
    
    flash('Transcription deleted successfully', 'success')
    return redirect(url_for('history'))

# === Admin Routes ===

@app.route('/admin')
@login_required
@admin_required
@track_activity
def admin():
    """Admin dashboard page"""
    days = request.args.get('days', 7, type=int)
    
    # Date range for filtering
    end_date = datetime.now()
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

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """Admin users management page"""
    # This would be implemented with a table of all users
    # and options to edit user details, toggle admin status, etc.
    return "Admin Users Management"

@app.route('/admin/transcriptions')
@login_required
@admin_required
def admin_transcriptions():
    """Admin transcriptions management page"""
    # This would be implemented with a table of all transcriptions
    # and options to view details, delete, etc.
    return "Admin Transcriptions Management"

# === Helper API Routes ===

@app.route('/api/add-notification', methods=['POST'])
def add_notification():
    """API endpoint to add a notification for a user"""
    if not current_user.is_authenticated and not request.is_json:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    user_id = data.get('user_id')
    message = data.get('message')
    
    if not user_id or not message:
        return jsonify({'error': 'Missing user_id or message'}), 400
    
    # Check if the user exists
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Only allow if current user is the user or an admin
    if current_user.id != user_id and not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Create the notification
    notification = Notification(
        user_id=user_id,
        message=message
    )
    
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({'success': True, 'notification_id': notification.id})

# Add this helper function to track transcriptions for users
def track_transcription(video_id, video_title, url, mode, lang, user_id=None, status='pending', duration=None, batch_id=None):
    """Record a transcription in the database"""
    transcription = Transcription(
        user_id=user_id,
        video_id=video_id,
        video_title=video_title,
        url=url,
        mode=mode,
        language=lang,
        duration=duration,
        status=status,
        batch_id=batch_id
    )
    
    db.session.add(transcription)
    db.session.commit()
    
    # If there's a user, send them a notification
    if user_id:
        user = User.query.get(user_id)
        if user and user.notification_site:
            notification = Notification(
                user_id=user_id,
                message=f"Transcription for '{video_title}' has been started."
            )
            db.session.add(notification)
            db.session.commit()
    
    return transcription.id

def update_transcription_status(transcription_id, status, error=None):
    """Update the status of a transcription"""
    transcription = Transcription.query.get(transcription_id)
    if not transcription:
        return False
    
    transcription.status = status
    if status == 'completed':
        transcription.completed_at = datetime.now()
    
    db.session.commit()
    
    # If the transcription is complete and the user has notifications enabled, send a notification
    if status == 'completed' and transcription.user_id:
        user = User.query.get(transcription.user_id)
        if user and user.notification_site:
            notification = Notification(
                user_id=transcription.user_id,
                message=f"Transcription for '{transcription.video_title}' is now complete!"
            )
            db.session.add(notification)
            db.session.commit()
    
    return True

# Function to update daily stats
def update_daily_stats():
    """Update daily statistics for admin dashboard"""
    today = datetime.now().date()
    
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
    
    return daily_stats

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """API endpoint for transcription"""
    # Check if we got JSON or form data
    if request.is_json:
        data = request.json
    else:
        data = request.form
    
    # Handle single video
    url = data.get('url')
    if url:
        mode = data.get('mode', 'auto')
        lang = data.get('lang', 'en')
        
        # Generate a job ID
        job_id = f"job_{int(time.time())}_{abs(hash(url)) % 10000}"
        
        # Extract video ID from URL
        import re
        video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
        if not video_id_match:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        video_id = video_id_match.group(1)
        video_title = f"YouTube Video ({video_id})"
        
        # For testing, return success immediately
        return jsonify({
            'job_id': job_id,
            'status': 'completed',
            'video_id': video_id,
            'video_title': video_title,
            'message': 'Transcription completed successfully (test mode)'
        })
    
    # Handle batch processing
    video_urls = data.get('video_urls')
    if video_urls:
        urls = [url.strip() for url in video_urls.split('\n') if url.strip()]
        job_id = f"batch_{int(time.time())}_{len(urls)}"
        
        return jsonify({
            'job_id': job_id,
            'status': 'completed',
            'video_count': len(urls),
            'message': f'Batch processing completed for {len(urls)} videos (test mode)'
        })
    
    # Handle playlist processing
    playlist_url = data.get('playlist_url')
    if playlist_url:
        job_id = f"playlist_{int(time.time())}"
        
        return jsonify({
            'job_id': job_id,
            'status': 'completed',
            'message': 'Playlist processing completed (test mode)'
        })
    
    return jsonify({'error': 'No valid input provided'}), 400

@app.route('/status/<job_id>')
def job_status(job_id):
    """Get job status"""
    # For testing, always return completed status
    return jsonify({
        'status': 'completed',
        'progress': 100,
        'message': 'Job completed successfully'
    })

@app.route('/download/<job_id>')
def download(job_id):
    """Download transcription endpoint"""
    format_type = request.args.get('format', 'txt')
    
    # For testing, return sample content
    sample_content = {
        'txt': "This is a sample transcription text for testing purposes.",
        'srt': """1
00:00:00,000 --> 00:00:05,000
This is a sample transcription

2
00:00:05,000 --> 00:00:10,000
for testing purposes.""",
        'vtt': """WEBVTT

00:00:00.000 --> 00:00:05.000
This is a sample transcription

00:00:05.000 --> 00:00:10.000
for testing purposes."""
    }
    
    content = sample_content.get(format_type, sample_content['txt'])
    
    # Create response with appropriate headers
    response = app.response_class(
        content,
        mimetype='text/plain',
        headers={
            'Content-Disposition': f'attachment; filename=transcription_{job_id}.{format_type}'
        }
    )
    return response