"""
WebSocket API for real-time progress updates. 

This module handles the WebSocket connections for providing real-time
progress updates for transcription jobs.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any, Set, List
import logging
import json

router = APIRouter()
logger = logging.getLogger(__name__)

# Dictionary to store active WebSocket connections
active_connections: Dict[str, Set[WebSocket]] = {}

@router.websocket("/ws/progress/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time progress updates.
    
    Args:
        websocket: WebSocket connection
        job_id: Unique job identifier
    """
    await websocket.accept()
    
    # Add connection to active connections
    if job_id not in active_connections:
        active_connections[job_id] = set()
    active_connections[job_id].add(websocket)
    
    try:
        # Import here to avoid circular imports
        from app.api.transcribe import job_statuses
        
        # Send initial status if available
        if job_id in job_statuses:
            await send_status_update(websocket, job_statuses[job_id])
        
        # Wait for disconnect
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            # Simply echo back any messages received (not used in current implementation)
            await websocket.send_text(data)
            
    except WebSocketDisconnect:
        # Remove connection from active connections
        if job_id in active_connections:
            active_connections[job_id].discard(websocket)
            if not active_connections[job_id]:
                del active_connections[job_id]
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        # Remove connection from active connections
        if job_id in active_connections:
            active_connections[job_id].discard(websocket)
            if not active_connections[job_id]:
                del active_connections[job_id]

async def send_status_update(websocket: WebSocket, status_data: Dict[str, Any]):
    """
    Send a status update to a WebSocket client.
    
    Args:
        websocket: WebSocket connection
        status_data: Status data to send
    """
    try:
        # Create a copy of the status data and remove any file paths
        # to avoid sending sensitive data to clients
        status_copy = status_data.copy()
        if "files" in status_copy:
            del status_copy["files"]
        
        await websocket.send_json(status_copy)
    except Exception as e:
        logger.error(f"Error sending status update: {e}")

async def broadcast_status_update(job_id: str, status_data: Dict[str, Any]):
    """
    Broadcast a status update to all connected clients for a job.
    
    Args:
        job_id: Unique job identifier
        status_data: Status data to send
    """
    if job_id not in active_connections:
        return
    
    # Get all WebSocket connections for the job
    connections = active_connections[job_id].copy()
    
    # Send update to all connections
    for connection in connections:
        try:
            await send_status_update(connection, status_data)
        except Exception as e:
            logger.error(f"Error broadcasting status update: {e}")
            # Remove connection if it's closed or has an error
            active_connections[job_id].discard(connection)
    
    # Clean up if no connections remain
    if not active_connections[job_id]:
        del active_connections[job_id]