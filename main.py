"""
Main entry point for the FastAPI application.
Configured to work properly with ASGI deployment.
"""
import os
import sys
import uvicorn
from app import create_app

# Create the FastAPI application instance
app = create_app()

if __name__ == "__main__":
    # For direct execution, use uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=5050, reload=True)