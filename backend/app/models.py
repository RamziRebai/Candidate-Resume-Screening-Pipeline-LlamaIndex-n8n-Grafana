from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
class WorkflowConfigRequest(BaseModel):
    """Configuration parameters for the workflow"""
    llm_model: str = Field(default="gpt-4o-mini", description="LLM model to use (gpt-4o, gpt-4o-mini, gpt-4-turbo)")
    embedding_model: str = Field(default="text-embedding-3-small", description="Embedding model to use. Larger models better capture nuances.")
    qdrant_index_name: str = Field(default="resume-application-matcher", description="Name of the Qdrant vector database collection")
    chunk_size: int = Field(default=200, ge=50, description="Size of text chunks for processing (minimum 50)")
    chunk_overlap: int = Field(default=0, ge=0, description="Overlap between chunks (minimum 0)")
    similarity_top_k: int = Field(default=7, ge=1, le=20, description="Number of similar chunks to retrieve")
    min_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum confidence score threshold")
    llm_temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="Temperature for LLM responses (0.0 = deterministic, 1.0 = creative)")

class UserFeedback(BaseModel):
    """User feedback for field improvements"""
    field: str
    feedback: str

class FeedbackRequest(BaseModel):
    """Request containing user feedback"""
    session_id: str
    feedbacks: List[UserFeedback]

class WorkflowResult(BaseModel):
    """Workflow execution result"""
    session_id: str
    status: str
    fields: List[Dict[str, Any]]
    monitoring_report: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class LogMessage(BaseModel):
    """Log message for real-time updates"""
    timestamp: str
    level: str
    message: str
    step: Optional[str] = None


    

