from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class RoomImage(BaseModel):
    url: str
    description: Optional[str] = None

class RoomAmenity(BaseModel):
    name: str
    icon: str
    description: Optional[str] = None

class RoomTypeResponse(BaseModel):
    id: str
    name: str
    description: str
    price: float
    min_occupancy: int
    max_occupancy: int
    beds: int
    bathrooms: int
    gallery: List[RoomImage]
    amenities: List[RoomAmenity]

class AvailabilityResponse(BaseModel):
    available: bool
    rooms: List[RoomTypeResponse]
    markdown_response: str

class BookingTicket(BaseModel):
    booking_id: str
    qr_code: str
    ticket_number: str
    booking_details: Dict[str, Any]

class BookingResponse(BaseModel):
    booking: Dict[str, Any]
    markdown_response: str
