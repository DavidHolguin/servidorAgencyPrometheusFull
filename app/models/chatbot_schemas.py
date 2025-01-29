"""Schemas for chatbot-related data."""
from typing import Optional, Dict, Any
from pydantic import BaseModel

class ChatbotBase(BaseModel):
    """Base schema for chatbots."""
    name: str
    description: str
    welcome_message: str
    context: str
    model_config: Dict[str, Any] = {
        "model": "gpt-4-turbo-preview",
        "temperature": 0.7,
        "max_tokens": 1000
    }
    theme_color: Optional[str] = "#007bff"
    icon_url: Optional[str] = None
    agency_id: str

class ChatbotCreate(ChatbotBase):
    """Schema for chatbot creation."""
    pass

class ChatbotResponse(ChatbotBase):
    """Schema for chatbot responses."""
    id: str
    created_at: str
    updated_at: Optional[str] = None
    is_active: bool = True
