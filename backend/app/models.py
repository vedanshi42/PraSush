from pydantic import BaseModel, Field
from typing import List, Optional

class GuidanceRequest(BaseModel):
    session_id: str = Field(..., description="Unique ID to track conversation session context")
    query: str = Field(..., description="User's query or description of what they are experiencing")
    image_data: Optional[str] = Field(None, description="Optional Base64 encoded image string captured by camera")
    user_name: Optional[str] = Field(None, description="Optional name of the user for friendly greeting")
    mode: str = Field("ask", description="Selected flow mode: 'repair', 'cook', 'ask', or 'learn'")

class GuidanceResponse(BaseModel):
    probable_issue: str = Field(..., description="AI diagnosed probable issue or task context")
    explanation: str = Field(..., description="Warm, friendly, easy-to-understand visual and logical explanation")
    is_dangerous: bool = Field(..., description="True if the situation presents danger, otherwise False")
    safety_warning: Optional[str] = Field(None, description="High-priority safety warnings or precautions. Direct to professional if dangerous")
    next_steps: List[str] = Field(..., description="Clean step-by-step checklist of actionable instructions")
    spoken_response: str = Field(..., description="Warm, human-friendly summary text optimized for text-to-speech output")

class ChatResponse(BaseModel):
    session_id: str
    response: GuidanceResponse
