import asyncio
import json
import logging
from typing import Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from app.api.transcribe import job_statuses

router = APIRouter()
logger = logging.getLogger(__name__)

# Store active connections
active_connections: Dict[str, WebSocket] = {}


@router.websocket("/ws/progress/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time progress updates.
    
    Args:
        websocket: WebSocket connection
        job_id: Unique job identifier
    """
    # Accept connection
    await websocket.accept()
    
    try:
        # Check if job exists
        if job_id not in job_statuses:
            await websocket.send_json({"error": "Job not found"})
            await websocket.close(code=1000)
            return
        
        # Add to active connections
        active_connections[job_id] = websocket
        
        # Send initial status
        await send_status_update(websocket, job_statuses[job_id])
        
        # Keep connection alive and send updates
        while True:
            # Check if job is still running
            if job_id not in job_statuses:
                await websocket.send_json({"error": "Job no longer exists"})
                break
            
            # Get current status
            current_status = job_statuses[job_id]
            
            # Send update
            await send_status_update(websocket, current_status)
            
            # If job is complete or has error, break loop
            if current_status["status"] in ["complete", "error"]:
                break
            
            # Wait before next update
            await asyncio.sleep(1)
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        # Remove from active connections
        if job_id in active_connections:
            del active_connections[job_id]
        
        # Close connection
        try:
            await websocket.close()
        except:
            pass


async def send_status_update(websocket: WebSocket, status_data: Dict[str, Any]):
    """
    Send a status update to a WebSocket client.
    
    Args:
        websocket: WebSocket connection
        status_data: Status data to send
    """
    try:
        await websocket.send_json({
            "status": status_data["status"],
            "percent": status_data["percent"],
            "error": status_data.get("error")
        })
    except Exception as e:
        logger.error(f"Error sending status update: {str(e)}")
        raise


async def broadcast_status_update(job_id: str, status_data: Dict[str, Any]):
    """
    Broadcast a status update to all connected clients for a job.
    
    Args:
        job_id: Unique job identifier
        status_data: Status data to send
    """
    if job_id in active_connections:
        try:
            await send_status_update(active_connections[job_id], status_data)
        except Exception as e:
            logger.error(f"Error broadcasting status update: {str(e)}")
