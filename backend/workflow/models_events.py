from typing import Optional, List
from typing_extensions import TypedDict

from pydantic import BaseModel, Field
from llama_index.core.workflow import Event
class ApplicationField(BaseModel):
    """Represents a field in the application form"""
    name: str = Field(..., description="The name/label of the application field")
    description: Optional[str] = Field(None, description="Additional context about the field")

class FieldResponse(BaseModel):
    """Represents a response to an application field"""
    field: str = Field(..., description="The application field name")
    response: str = Field(..., description="The generated response based on resume data")
    confidence_scores: Optional[list[float]] = Field(None, description="Confidence score for the response")

class FormFields(BaseModel):
    """Collection of application form fields"""
    fields: List[str] = Field(..., description="List of fields that need to be filled")

class HumanFeedback(TypedDict):
    """Human feedback structure"""
    field: str
    feedback: str

class FeedbackCollection(BaseModel):
    """Collection of human feedbacks"""
    feedbacks: Optional[List[HumanFeedback]] = Field(
        default=None, 
        description="List of fields and their relevant feedbacks from human reviewer"
    )

# Event definitions for the workflow
class ParseFormEvent(Event):
    """Event triggered when form parsing is complete"""
    application_form: str
    resume_file: str

class GenerateQuestionsEvent(Event):
    """Event triggered to generate questions for form fields"""
    pass

class QueryEvent(Event):
    """Event for querying resume data for specific fields"""
    query: str
    field: str

class ResponseEvent(Event):
    """Event containing response for a specific field"""
    response: str
    field: str
    confidence_scores: Optional[list[float]] = None

class FeedbackEvent(Event):
    """Event containing human feedback for improvements"""
    feedbacks: List[HumanFeedback]

class LogEvent(Event):
    """Event containg log events"""
    log: str

# ================================================================================
# UTILITY FUNCTIONS

