# How to Fix the ASGI/Workflow Issue

## The Problem
Your FastAPI app keeps getting a 500 error because:
- The Replit workflow is configured to use: `gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app`
- This uses **WSGI protocol** (sync workers)
- But FastAPI requires **ASGI protocol**
- Result: `TypeError: FastAPI.__call__() missing 1 required positional argument: 'send'`

## The Solution (3 Options)

### Option 1: Manual Shell Command (Immediate Fix)
1. Stop the current workflow (click Stop button)
2. Open the Shell tab in Replit
3. Run this command:
```bash
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

### Option 2: Use the Script I Created
1. Stop the current workflow
2. In the Shell, run:
```bash
python start_uvicorn.py
```

### Option 3: Fix the Workflow Configuration (Permanent Fix)
The workflow configuration in `.replit` needs to be changed from:
```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```
To:
```bash
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

Since I cannot edit the `.replit` file directly, you may need to:
1. Go to the `.replit` file
2. Change line 29 from the gunicorn command to the uvicorn command above

## Verification
Once using uvicorn, you should see:
- ✓ "INFO: Started server process"
- ✓ "INFO: Application startup complete"
- ✓ "INFO: Uvicorn running on http://0.0.0.0:5000"
- ✓ No more 500 errors

## Why This Works
- **uvicorn**: ASGI server (correct for FastAPI)
- **gunicorn**: WSGI server (wrong for FastAPI unless using uvicorn workers)
- FastAPI requires ASGI protocol for WebSockets, async features, and proper request handling

Your FastAPI application code is perfect - it just needs the right server!