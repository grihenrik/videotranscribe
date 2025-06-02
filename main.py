from flask_app import app
import routes
import auth  
import user_routes
import admin_routes

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)