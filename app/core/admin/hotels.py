"""Hotel management module."""
from typing import Dict, Any, List, Optional
from .base import BaseEntityManager

class HotelManager(BaseEntityManager):
    """Manager for hotel operations."""
    
    def __init__(self, agency_id: str):
        super().__init__(agency_id, "hotels")
        
    def create_hotel(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new hotel with validation."""
        required_fields = ["name", "description", "address", "city", "country"]
        
        # Validate required fields
        for field in required_fields:
            if field not in data:
                return self.format_response(False, f"Missing required field: {field}")
        
        # Ensure amenities is a list
        if "amenities" in data and not isinstance(data["amenities"], list):
            return self.format_response(False, "Amenities must be a list")
            
        return self.create_item(data)
    
    def update_hotel(self, hotel_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update hotel with validation."""
        if "amenities" in data and not isinstance(data["amenities"], list):
            return self.format_response(False, "Amenities must be a list")
            
        return self.update_item(hotel_id, data)
    
    def get_hotel_rooms(self, hotel_id: str) -> Dict[str, Any]:
        """Get all rooms for a hotel."""
        if not self.validate_ownership("hotels", hotel_id):
            return self.format_response(False, "Hotel not found or access denied")
            
        # Get room types for the hotel
        room_types = self.supabase.table("room_types")\
            .select("*")\
            .eq("hotel_id", hotel_id)\
            .execute()
            
        # Get rooms for each room type
        all_rooms = []
        for room_type in room_types.data:
            rooms = self.supabase.table("rooms")\
                .select("*")\
                .eq("room_type_id", room_type["id"])\
                .execute()
            all_rooms.extend(rooms.data)
            
        return self.format_response(True, "Rooms retrieved", {
            "room_types": room_types.data,
            "rooms": all_rooms
        })
    
    def get_hotel_bookings(
        self, 
        hotel_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get bookings for a hotel."""
        if not self.validate_ownership("hotels", hotel_id):
            return self.format_response(False, "Hotel not found or access denied")
            
        query = self.supabase.table("bookings")\
            .select("*")\
            .eq("booking_type", "room")
            
        if start_date:
            query = query.gte("check_in", start_date)
        if end_date:
            query = query.lte("check_out", end_date)
            
        response = query.execute()
            
        return self.format_response(True, "Bookings retrieved", {
            "bookings": response.data
        })
    
    def get_hotel_stats(self, hotel_id: str) -> Dict[str, Any]:
        """Get hotel statistics."""
        if not self.validate_ownership("hotels", hotel_id):
            return self.format_response(False, "Hotel not found or access denied")
            
        response = self.supabase.rpc(
            'get_hotel_stats',
            {'p_hotel_id': hotel_id}
        ).execute()
        
        return self.format_response(True, "Statistics retrieved", response.data[0] if response.data else {})
    
    def update_room_status(self, room_id: str, status: str) -> Dict[str, Any]:
        """Update the status of a room."""
        # Validate room belongs to a hotel owned by the agency
        room = self.supabase.table("rooms").select("*").eq("id", room_id).execute()
        if not room.data:
            return self.format_response(False, "Room not found")
            
        room_type = self.supabase.table("room_types")\
            .select("hotel_id")\
            .eq("id", room.data[0]["room_type_id"])\
            .execute()
            
        if not room_type.data or not self.validate_ownership("hotels", room_type.data[0]["hotel_id"]):
            return self.format_response(False, "Room not found or access denied")
            
        # Update room status
        response = self.supabase.table("rooms")\
            .update({"status": status})\
            .eq("id", room_id)\
            .execute()
            
        return self.format_response(True, "Room status updated", {"room": response.data[0] if response.data else None})
    
    def check_room_availability(
        self,
        hotel_id: str,
        check_in: str,
        check_out: str,
        room_type_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check room availability for given dates."""
        if not self.validate_ownership("hotels", hotel_id):
            return self.format_response(False, "Hotel not found or access denied")
            
        response = self.supabase.rpc(
            'check_room_availability',
            {
                'p_hotel_id': hotel_id,
                'p_room_type_id': room_type_id,
                'p_check_in': check_in,
                'p_check_out': check_out
            }
        ).execute()
        
        return self.format_response(True, "Availability checked", response.data[0] if response.data else {})
