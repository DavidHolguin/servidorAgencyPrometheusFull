"""Chatbot management module."""
from typing import Dict, Any, Optional
from .base import BaseEntityManager

class ChatbotManager(BaseEntityManager):
    """Manager for chatbot operations."""
    
    def __init__(self, agency_id: str):
        super().__init__(agency_id, "chatbots")
        
    def create_chatbot(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new chatbot with validation."""
        required_fields = ["name", "description"]
        
        # Validate required fields
        for field in required_fields:
            if field not in data:
                return self.format_response(False, f"Missing required field: {field}")
        
        # Add default configuration if not provided
        if "configuration" not in data:
            data["configuration"] = {
                "temperature": 0.7,
                "model": "gpt-4-turbo-preview",
                "context_length": 10
            }
            
        return self.create_item(data)
    
    def update_chatbot(self, chatbot_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update chatbot with validation."""
        # Get current chatbot data
        current = self.get_item(chatbot_id)
        if not current["success"]:
            return current
            
        # Merge configuration if provided
        if "configuration" in data:
            current_config = current["data"]["item"]["configuration"]
            data["configuration"] = {**current_config, **data["configuration"]}
            
        return self.update_item(chatbot_id, data)
    
    def get_chatbot_stats(self, chatbot_id: str) -> Dict[str, Any]:
        """Get chatbot usage statistics."""
        if not self.validate_ownership("chatbots", chatbot_id):
            return self.format_response(False, "Chatbot not found or access denied")
            
        # Get messages statistics
        messages_query = """
        SELECT 
            COUNT(*) as total_messages,
            COUNT(DISTINCT lead_id) as total_leads,
            AVG(CASE WHEN is_bot THEN 1 ELSE 0 END) as bot_message_ratio
        FROM chat_messages 
        WHERE chatbot_id = ?
        """
        
        response = self.supabase.rpc(
            'get_chatbot_stats',
            {'p_chatbot_id': chatbot_id}
        ).execute()
        
        return self.format_response(True, "Statistics retrieved", response.data[0] if response.data else {})
    
    def get_chatbot_conversations(
        self, 
        chatbot_id: str, 
        limit: int = 10, 
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get recent conversations for a chatbot."""
        if not self.validate_ownership("chatbots", chatbot_id):
            return self.format_response(False, "Chatbot not found or access denied")
            
        response = self.supabase.table("chat_messages")\
            .select("*")\
            .eq("chatbot_id", chatbot_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .offset(offset)\
            .execute()
            
        return self.format_response(True, "Conversations retrieved", {
            "messages": response.data,
            "total": len(response.data),
            "has_more": len(response.data) == limit
        })
        
    def update_chatbot_context(self, chatbot_id: str, context: str) -> Dict[str, Any]:
        """Update the context/prompt of a chatbot."""
        return self.update_item(chatbot_id, {"context": context})
        
    def toggle_chatbot_status(self, chatbot_id: str, is_active: bool) -> Dict[str, Any]:
        """Toggle chatbot active status."""
        return self.update_item(chatbot_id, {
            "configuration": {
                "is_active": is_active
            }
        })
