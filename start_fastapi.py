#!/usr/bin/env python
"""
Standalone script to run the FastAPI application with uvicorn
This is used as the entry point for the Replit workflow
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)