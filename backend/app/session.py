import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import WebSocket

from app.models import WorkflowConfigRequest

logger = logging.getLogger(__name__)
class SessionManager:
    """Manage workflow sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.websocket_connections: Dict[str, WebSocket] = {}
    
    def create_session(self, config: WorkflowConfigRequest) -> str:
        """Create a new workflow session"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "id": session_id,
            "config": config,
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "resume_file": None,
            "application_form": None,
            "workflow": None,
            "monitor": None,
            "results": None,
            "logs": []
        }
        logger.info(f"Created session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def update_session_status(self, session_id: str, status: str):
        """Update session status"""
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = status
            self.sessions[session_id]["updated_at"] = datetime.now().isoformat()
    
    def add_log(self, session_id: str, level: str, message: str, step: str = None):
        """Add log message to session"""
        if session_id in self.sessions:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message,
                "step": step
            }
            self.sessions[session_id]["logs"].append(log_entry)
            
            # Send to WebSocket if connected
            if session_id in self.websocket_connections:
                asyncio.create_task(self.send_log_to_websocket(session_id, log_entry))
    
    async def send_log_to_websocket(self, session_id: str, log_entry: dict):
        """Send log message via WebSocket"""
        if session_id in self.websocket_connections:
            try:
                websocket = self.websocket_connections[session_id]
                await websocket.send_text(json.dumps({
                    "type": "log",
                    "data": log_entry
                }))
            except Exception as e:
                logger.error(f"Failed to send log via WebSocket: {e}")
    
    def add_websocket(self, session_id: str, websocket: WebSocket):
        """Add WebSocket connection"""
        self.websocket_connections[session_id] = websocket
    
    def remove_websocket(self, session_id: str):
        """Remove WebSocket connection"""
        if session_id in self.websocket_connections:
            del self.websocket_connections[session_id]

# Global session manager
session_manager = SessionManager()

# ================================================================================
# CUSTOM LOG HANDLER FOR REAL-TIME UPDATES
# ================================================================================

class WebSocketLogHandler(logging.Handler):
    """Custom log handler that sends logs via WebSocket"""
    
    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id
    
    def emit(self, record):
        """Emit log record to WebSocket"""
        try:
            log_message = self.format(record)
            session_manager.add_log(
                self.session_id,
                record.levelname.lower(),
                log_message,
                getattr(record, 'step', None)
            )
        except Exception:
            pass

# ================================================================================
# API ENDPOINTS

# Global session manager
session_manager = SessionManager()

