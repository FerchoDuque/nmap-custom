from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from typing import Dict, Set
import json
import asyncio
import logging

from app.database import get_db
from app.models.scan import Scan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """WebSocket connection manager"""
    
    def __init__(self):
        # Map of scan_id to set of connected websockets
        self.active_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, scan_id: int):
        """Connect a websocket to a scan"""
        await websocket.accept()
        
        if scan_id not in self.active_connections:
            self.active_connections[scan_id] = set()
        
        self.active_connections[scan_id].add(websocket)
        logger.info(f"WebSocket connected to scan {scan_id}")
    
    def disconnect(self, websocket: WebSocket, scan_id: int):
        """Disconnect a websocket from a scan"""
        if scan_id in self.active_connections:
            self.active_connections[scan_id].discard(websocket)
            
            if not self.active_connections[scan_id]:
                del self.active_connections[scan_id]
        
        logger.info(f"WebSocket disconnected from scan {scan_id}")
    
    async def send_update(self, scan_id: int, message: dict):
        """Send update to all connected clients for a scan"""
        if scan_id not in self.active_connections:
            return
        
        # Remove disconnected clients
        disconnected = set()
        
        for websocket in self.active_connections[scan_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to websocket: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket, scan_id)


# Global connection manager
manager = ConnectionManager()


# ============================================================================
# Contract payload builders (pure functions, unit-testable without sockets)
# ============================================================================

TERMINAL_STATUSES = ("completed", "failed", "cancelled")


def scan_snapshot(scan: Scan) -> Dict[str, object]:
    """Build the mutable progress snapshot shared by `status` and `update`."""
    return {
        "status": scan.status.value,
        "progress": scan.progress,
        "current_host": scan.current_host,
        "hosts_scanned": scan.hosts_scanned,
        "ports_found": scan.total_ports_found,
        "error_message": scan.error_message,
    }


def build_status_message(scan: Scan) -> Dict[str, object]:
    """Initial `status` message sent right after the connection is accepted."""
    return {
        "type": "status",
        "scan_id": scan.id,
        **scan_snapshot(scan),
        "hosts_total": scan.hosts_total,
    }


def build_update_message(scan: Scan) -> Dict[str, object]:
    """`update` message sent when the persisted snapshot changes."""
    return {
        "type": "update",
        "scan_id": scan.id,
        **scan_snapshot(scan),
        "hosts_total": scan.hosts_total,
    }


def build_error_message(scan_id: int, message: str) -> Dict[str, object]:
    """`error` message sent when the scan cannot be streamed."""
    return {"type": "error", "scan_id": scan_id, "message": message}


@router.websocket("/scan/{scan_id}")
async def websocket_scan_progress(websocket: WebSocket, scan_id: int):
    """
    WebSocket endpoint for real-time scan progress updates.
    
    Args:
        websocket: WebSocket connection
        scan_id: Scan ID to monitor
    """
    await manager.connect(websocket, scan_id)
    
    db = None
    try:
        # Send initial scan status
        from app.database import SessionLocal
        db = SessionLocal()

        scan = db.query(Scan).filter(Scan.id == scan_id).first()

        if not scan:
            await websocket.send_json(build_error_message(scan_id, f"Scan {scan_id} not found"))
            await websocket.close()
            return

        await websocket.send_json(build_status_message(scan))

        # Keep connection alive and poll for updates
        last_data = scan_snapshot(scan)

        # Terminal scans have nothing left to stream: emit state and close.
        if scan.status.value in TERMINAL_STATUSES:
            await websocket.close()
            return

        while True:
            try:
                # 1. Listen for client messages (non-blockingish via wait_for)
                # We use a short timeout to allow polling loop to run
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=0.5)
                    if data == "ping":
                        await websocket.send_text("pong")
                except asyncio.TimeoutError:
                    pass
                
                # 2. Poll Database for updates
                db.refresh(scan)

                current_data = {
                    "status": scan.status.value,
                    "progress": scan.progress,
                    "current_host": scan.current_host,
                    "hosts_scanned": scan.hosts_scanned,
                    "ports_found": scan.total_ports_found,
                    "error_message": scan.error_message,
                }

                # If changed, send update
                changed = current_data != last_data
                if changed:
                    await websocket.send_json(build_update_message(scan))
                    last_data = current_data

                # Check if scan finished: always emit a final state, but never twice
                if scan.status.value in TERMINAL_STATUSES:
                    if not changed:
                        await websocket.send_json(build_update_message(scan))
                    await websocket.close()
                    break
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                break
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, scan_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, scan_id)
    finally:
        if db is not None:
            db.close()


async def broadcast_scan_update(scan_id: int, update: dict):
    """
    Broadcast scan update to all connected clients.
    
    Args:
        scan_id: Scan ID
        update: Update data
    """
    await manager.send_update(scan_id, {
        "type": "update",
        "scan_id": scan_id,
        **update
    })
