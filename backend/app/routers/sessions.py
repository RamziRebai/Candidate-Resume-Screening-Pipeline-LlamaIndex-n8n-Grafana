import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect

from workflow_components import EnhancedWorkflowConfig, WorkflowMonitor, IntelligentResumeMatchingWorkflow

from app.models import WorkflowConfigRequest, FeedbackRequest
from app.session import session_manager
from app.services.workflow_runtime import execute_workflow, process_feedback

logger = logging.getLogger(__name__)
router = APIRouter()
@router.post("/api/sessions", response_model=dict)
async def create_session(config: WorkflowConfigRequest):
    """Create a new workflow session with configuration"""
    try:
        session_id = session_manager.create_session(config)
        return {
            "session_id": session_id,
            "status": "created",
            "message": "Session created successfully"
        }
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/sessions/{session_id}/upload")
async def upload_files(
    session_id: str,
    resume: UploadFile = File(...),
    application_form: UploadFile = File(...)
):
    """Upload resume and application form files"""
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Create upload directory
        upload_dir = Path(f"uploads/{session_id}")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save files
        resume_path = upload_dir / f"resume_{resume.filename}"
        form_path = upload_dir / f"form_{application_form.filename}"
        
        with open(resume_path, "wb") as f:
            content = await resume.read()
            f.write(content)
        
        with open(form_path, "wb") as f:
            content = await application_form.read()
            f.write(content)
        
        # Update session
        session["resume_file"] = str(resume_path)
        session["application_form"] = str(form_path)
        session_manager.update_session_status(session_id, "files_uploaded")
        
        session_manager.add_log(
            session_id, "info", 
            f"Files uploaded successfully: {resume.filename}, {application_form.filename}"
        )
        
        return {
            "status": "success",
            "message": "Files uploaded successfully",
            "resume_file": resume.filename,
            "application_form": application_form.filename
        }
        
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        session_manager.add_log(session_id, "error", f"File upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/sessions/{session_id}/start")
async def start_workflow(session_id: str, background_tasks: BackgroundTasks):
    """Start the workflow execution"""
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not session["resume_file"] or not session["application_form"]:
            raise HTTPException(status_code=400, detail="Files not uploaded")
        
        # Add background task
        background_tasks.add_task(execute_workflow, session_id)
        
        session_manager.update_session_status(session_id, "processing")
        session_manager.add_log(session_id, "info", "Workflow execution started")
        
        return {
            "status": "started",
            "message": "Workflow execution started in background"
        }
        
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        session_manager.add_log(session_id, "error", f"Failed to start workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get session status and logs"""
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        status = session["status"]
        if status == "waiting_feedback":
            status = "awaiting_review"

        results = session.get("results")
        if isinstance(results, dict) and results.get("status") == "waiting_feedback":
            results = {**results, "status": "awaiting_review"}

        return {
            "session_id": session_id,
            "status": status,
            "logs": session["logs"][-50:],  # Last 50 logs
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Failed to get session status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/sessions/{session_id}/feedback")
async def submit_feedback(session_id: str, feedback: FeedbackRequest, background_tasks: BackgroundTasks):
    """Submit user feedback for field improvements"""
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Add background task for feedback processing
        background_tasks.add_task(process_feedback, session_id, feedback.feedbacks)
        
        session_manager.update_session_status(session_id, "processing_feedback")
        session_manager.add_log(
            session_id, "info", 
            f"Processing feedback for {len(feedback.feedbacks)} fields"
        )
        
        return {
            "status": "feedback_received",
            "message": "Feedback submitted successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to process feedback: {e}")
        session_manager.add_log(session_id, "error", f"Failed to process feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/sessions/{session_id}/results")
async def get_results(session_id: str):
    """Get workflow results"""
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        results = session.get("results")
        if not results:
            return {"status": "no_results", "message": "No results available yet"}
        
        return results
    except Exception as e:
        logger.error(f"Failed to get results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/sessions/{session_id}/debug")
async def get_debug_info(session_id: str):
    """Get debug information for troubleshooting"""
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        debug_info = {
            "session_id": session_id,
            "status": session["status"],
            "has_results": bool(session.get("results")),
            "results_type": type(session.get("results")).__name__ if session.get("results") else None,
            "has_workflow": bool(session.get("workflow")),
            "has_workflow_handler": bool(session.get("workflow_handler")),
            "resume_file": session.get("resume_file"),
            "application_form": session.get("application_form"),
            "logs_count": len(session.get("logs", [])),
            "recent_logs": session.get("logs", [])[-5:] if session.get("logs") else []
        }
        
        if session.get("results"):
            debug_info["results_keys"] = list(session["results"].keys()) if isinstance(session["results"], dict) else "Not a dict"
            if isinstance(session["results"], dict) and "fields" in session["results"]:
                debug_info["fields_count"] = len(session["results"]["fields"])
        
        return debug_info
        
    except Exception as e:
        logger.error(f"Failed to get debug info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test workflow import
        config = EnhancedWorkflowConfig()
        monitor = WorkflowMonitor()
        workflow = IntelligentResumeMatchingWorkflow(config=config, monitor=monitor)
        
        return {
            "status": "healthy",
            "message": "All components loaded successfully",
            "workflow_loaded": True,
            "session_count": len(session_manager.sessions)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": str(e),
            "workflow_loaded": False
        }

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    session_manager.add_websocket(session_id, websocket)
    
    logger.info(f"WebSocket connected for session: {session_id}")
    
    try:
        # Send a test message to verify connection
        await websocket.send_text(json.dumps({
            "type": "workflow_log",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "level": "info",
                "message": "WebSocket connection established - ready to receive workflow logs",
                "step": "connection",
                "type": "workflow_log"
            }
        }))
        
        # Keep connection alive indefinitely - just wait for disconnect
        try:
            while True:
                # Wait for pings or any client messages (but don't require them)
                try:
                    # Set a long timeout to avoid blocking
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                    # If client sends ping, send pong
                    if data == "ping":
                        await websocket.send_text("pong")
                except asyncio.TimeoutError:
                    # Timeout is expected - just continue the loop
                    # Send a small heartbeat to check if connection is still alive
                    try:
                        await websocket.ping()
                    except:
                        # If ping fails, connection is dead
                        break
                except Exception:
                    # Any other exception means connection issues
                    break
        except Exception:
            pass
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
    finally:
        session_manager.remove_websocket(session_id)
        logger.info(f"WebSocket disconnected for session: {session_id}")

