"""Database operations module."""
from typing import Dict, List, Optional, Any
from app.core.supabase import get_supabase_client

class Database:
    """Database operations handler."""
    
    def __init__(self):
        """Initialize database connection."""
        self.supabase = get_supabase_client()
        
    async def list_chatbots(self, agency_id: str) -> List[Dict[str, Any]]:
        """List all chatbots for an agency."""
        try:
            response = self.supabase.table('chatbots').select('*').eq('agency_id', agency_id).execute()
            return response.data
        except Exception as e:
            print(f"Error listing chatbots: {str(e)}")
            return []
            
    async def create_chatbot(self, chatbot_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new chatbot."""
        try:
            response = self.supabase.table('chatbots').insert(chatbot_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating chatbot: {str(e)}")
            raise
            
    async def get_chatbot(self, chatbot_id: str) -> Optional[Dict[str, Any]]:
        """Get a chatbot by ID."""
        try:
            response = self.supabase.table('chatbots').select('*').eq('id', chatbot_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting chatbot: {str(e)}")
            return None
            
    async def update_chatbot(self, chatbot_id: str, chatbot_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a chatbot."""
        try:
            response = self.supabase.table('chatbots').update(chatbot_data).eq('id', chatbot_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error updating chatbot: {str(e)}")
            raise
            
    async def delete_chatbot(self, chatbot_id: str) -> bool:
        """Delete a chatbot."""
        try:
            response = self.supabase.table('chatbots').delete().eq('id', chatbot_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error deleting chatbot: {str(e)}")
            raise
