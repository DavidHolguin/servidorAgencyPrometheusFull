"""Base classes for admin modules."""
from typing import Dict, Any, Optional
from app.core.supabase import get_supabase_client

class BaseAdminModule:
    """Base class for all admin modules."""
    
    def __init__(self, agency_id: str):
        self.agency_id = agency_id
        self.supabase = get_supabase_client()
        
    def validate_ownership(self, table: str, item_id: str) -> bool:
        """Validate if an item belongs to the agency."""
        response = self.supabase.table(table).select("*").eq("id", item_id).eq("agency_id", self.agency_id).execute()
        return bool(response.data)

    def format_response(self, success: bool, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format standard response."""
        return {
            "success": success,
            "message": message,
            "data": data or {}
        }

class BaseEntityManager(BaseAdminModule):
    """Base class for entity management."""
    
    def __init__(self, agency_id: str, table_name: str):
        super().__init__(agency_id)
        self.table_name = table_name
    
    def list_items(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """List items with optional filters."""
        query = self.supabase.table(self.table_name).select("*").eq("agency_id", self.agency_id)
        
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
                
        response = query.execute()
        return self.format_response(True, f"Retrieved {len(response.data)} items", {"items": response.data})
    
    def get_item(self, item_id: str) -> Dict[str, Any]:
        """Get a single item by ID."""
        if not self.validate_ownership(self.table_name, item_id):
            return self.format_response(False, "Item not found or access denied")
            
        response = self.supabase.table(self.table_name).select("*").eq("id", item_id).execute()
        return self.format_response(True, "Item retrieved", {"item": response.data[0] if response.data else None})
    
    def create_item(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new item."""
        data["agency_id"] = self.agency_id
        response = self.supabase.table(self.table_name).insert(data).execute()
        return self.format_response(True, "Item created successfully", {"item": response.data[0] if response.data else None})
    
    def update_item(self, item_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing item."""
        if not self.validate_ownership(self.table_name, item_id):
            return self.format_response(False, "Item not found or access denied")
            
        response = self.supabase.table(self.table_name).update(data).eq("id", item_id).execute()
        return self.format_response(True, "Item updated successfully", {"item": response.data[0] if response.data else None})
    
    def delete_item(self, item_id: str) -> Dict[str, Any]:
        """Delete an item."""
        if not self.validate_ownership(self.table_name, item_id):
            return self.format_response(False, "Item not found or access denied")
            
        response = self.supabase.table(self.table_name).delete().eq("id", item_id).execute()
        return self.format_response(True, "Item deleted successfully")
