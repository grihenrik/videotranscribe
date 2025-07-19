#!/bin/bash
# Production startup script for FastAPI application
# This ensures the correct ASGI server configuration

echo "Starting FastAPI application with proper ASGI configuration..."

# Kill any existing processes
pkill -f gunicorn 2>/dev/null
pkill -f uvicorn 2>/dev/null
sleep 1

# Start with gunicorn using uvicorn workers
exec gunicorn \
    --bind 0.0.0.0:5000 \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 1 \
    --timeout 120 \
    --keep-alive 5 \
    --reload \
    --access-logfile - \
    --error-logfile - \
    main:app