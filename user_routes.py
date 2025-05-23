import os
import datetime
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user, logout_user
from sqlalchemy import func, desc

from app import db
from models import User, Transcription, Notification, DailyStats
from auth import admin_required

# Create user management blueprint
user_bp = Blueprint('user', __name__)

# === User Profile Routes ===

@user_bp.route('/settings')
@login_required
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
    
    # Format duration
    hours = total_duration // 3600
    minutes = (total_duration % 3600) // 60
    seconds = total_duration % 60
    total_duration_formatted = f"{hours}:{minutes:02d}:{seconds:02d}"
    
    stats = {
        'total_transcriptions': total_transcriptions,
        'total_duration_formatted': total_duration_formatted,
        'success_rate': success_rate
    }
    
    return render_template('settings.html', stats=stats)

@user_bp.route('/update-notification-settings', methods=['POST'])
@login_required
def update_notification_settings():
    """Update user notification settings"""
    notification_email = 'notification_email' in request.form
    notification_site = 'notification_site' in request.form
    
    current_user.notification_email = notification_email
    current_user.notification_site = notification_site
    db.session.commit()
    
    flash('Notification settings updated successfully', 'success')
    return redirect(url_for('user.settings'))

@user_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account and all associated data"""
    if 'confirm_delete' in request.form:
        # Delete user's notifications
        Notification.query.filter_by(user_id=current_user.id).delete()
        
        # Remove user ID from transcriptions but keep the transcriptions
        Transcription.query.filter_by(user_id=current_user.id).update({Transcription.user_id: None})
        
        # Delete OAuth tokens
        from models import OAuth
        OAuth.query.filter_by(user_id=current_user.id).delete()
        
        # Delete the user
        user_id = current_user.id
        db.session.delete(current_user._get_current_object())
        db.session.commit()
        
        # Log out the user
        logout_user()
        
        flash('Your account has been deleted successfully', 'success')
        return redirect(url_for('index'))
    
    flash('Please confirm the account deletion', 'danger')
    return redirect(url_for('user.settings'))

# === User Transcription History ===

@user_bp.route('/history')
@login_required
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
    
    # Format duration
    hours = total_duration // 3600
    minutes = (total_duration % 3600) // 60
    seconds = total_duration % 60
    total_duration_formatted = f"{hours}:{minutes:02d}:{seconds:02d}"
    
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
        'total_duration': total_duration_formatted,
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

@user_bp.route('/delete-transcription', methods=['POST'])
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
    return redirect(url_for('user.history'))

# === Notification Management ===

@user_bp.route('/notifications')
@login_required
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

@user_bp.route('/mark-notification-read/<int:notification_id>')
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
    return redirect(url_for('user.notifications'))

@user_bp.route('/mark-all-read')
@login_required
def mark_all_read():
    """Mark all notifications as read"""
    Notification.query.filter_by(
        user_id=current_user.id,
        read=False
    ).update({Notification.read: True})
    
    db.session.commit()
    
    flash('All notifications marked as read', 'success')
    return redirect(url_for('user.notifications'))

@user_bp.route('/delete-notification/<int:notification_id>')
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
    return redirect(url_for('user.notifications'))

# Add notification API endpoint

@user_bp.route('/api/add-notification', methods=['POST'])
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