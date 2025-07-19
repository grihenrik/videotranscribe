"""
Main server entry point that works with both gunicorn and uvicorn
This file provides the 'app' object that gunicorn expects to find
"""

# Import the FastAPI app
from main import app

# For gunicorn compatibility, we need to expose the app directly
# The app object is already a FastAPI instance, which is ASGI compatible
# but the workflow is trying to use WSGI gunicorn workers

if __name__ == "__main__":
    # For direct execution, use uvicorn
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, reload=True)