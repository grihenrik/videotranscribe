import os
import logging
from app import app, db
import models  # Import models to register them with SQLAlchemy
import auth
import user_routes
import admin_routes
import run

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Register blueprints
app.register_blueprint(auth.auth_bp, url_prefix='/auth')
app.register_blueprint(user_routes.user_bp, url_prefix='/user')
app.register_blueprint(admin_routes.admin_bp, url_prefix='/admin')

# Import routes from run.py for the main app
app.route("/")(run.index)
app.route("/batch")(run.batch)
app.route("/playlist")(run.playlist)
app.route("/settings")(run.settings_redirect)
app.route("/history")(run.history_redirect)
app.route("/notifications")(run.notifications_redirect)
app.route("/admin")(run.admin_redirect)
app.route("/transcribe", methods=["POST"])(run.transcribe)
app.route("/job-status/<job_id>")(run.job_status)
app.route("/download/<job_id>")(run.download)

# Start the worker thread
run.ensure_worker_thread()

# Update daily stats
run.update_daily_stats()

# Main entry point for direct execution
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)