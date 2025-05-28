# Main entry point for the Flask application with dashboard functionality
from flask_app import app  # Import the Flask app from flask_app.py
import routes  # This loads all our routes including the new dashboard
import auth    # This loads authentication routes
import models  # Import models to ensure database tables are created

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)