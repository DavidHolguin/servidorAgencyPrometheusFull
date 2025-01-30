# app/models/schemas.py
from pydantic import BaseModel, Field, constr
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class Channel(str, Enum):
    WEB = "web"
    WHATSAPP = "whatsapp"
    MESSENGER = "messenger"
    TELEGRAM = "telegram"

class Message(BaseModel):
    """
    Modelo para los mensajes entrantes al chatbot
    """
    chatbot_id: str = Field(..., description="ID único del chatbot que procesará el mensaje")
    message: str = Field(..., description="Contenido del mensaje del usuario")
    lead_id: Optional[str] = Field(None, description="ID único del usuario o conversación")
    channel: Optional[Channel] = Field(Channel.WEB, description="Canal por el que se recibe el mensaje")
    audio_content: Optional[str] = Field(None, description="Contenido del mensaje de audio en base64")
    metadata: Optional[Dict[str, Any]] = Field(
        default={},
        description="Metadatos adicionales del mensaje (ej: ubicación, preferencias)"
    )

class MessageResponse(BaseModel):
    """
    Modelo para las respuestas del chatbot
    """
    response: str = Field(..., description="Respuesta generada por el chatbot")
    suggested_actions: Optional[List[str]] = Field(
        default=None,
        description="Lista de acciones sugeridas para el usuario"
    )
    context: Optional[Dict[str, Any]] = Field(
        default={},
        description="Contexto adicional de la respuesta"
    )

class WhatsAppMessage(BaseModel):
    """
    Modelo para mensajes entrantes de WhatsApp
    """
    object: str = Field(..., description="Tipo de objeto de WhatsApp")
    entry: List[Dict[str, Any]] = Field(..., description="Lista de eventos de WhatsApp")

class GuestInfo(BaseModel):
    """
    Información del huésped para una reserva
    """
    name: str = Field(..., description="Nombre completo del huésped")
    email: str = Field(..., description="Correo electrónico del huésped", pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    phone: str = Field(..., description="Número de teléfono del huésped")
    document_type: Optional[str] = Field(None, description="Tipo de documento de identidad")
    document_number: Optional[str] = Field(None, description="Número de documento de identidad")

class BookingItem(BaseModel):
    """
    Elemento individual de una reserva (habitación, tour, etc.)
    """
    item_id: str = Field(..., description="ID único del item (habitación, tour, etc.)")
    item_type: str = Field(..., description="Tipo de item (room, tour, transfer, etc.)")
    quantity: int = Field(..., description="Cantidad de items")
    price: float = Field(..., description="Precio por unidad")
    details: Optional[Dict[str, Any]] = Field(default={}, description="Detalles adicionales del item")

class BookingRequest(BaseModel):
    """
    Modelo para solicitudes de reserva
    """
    user_id: str = Field(..., description="ID único del usuario que realiza la reserva")
    hotel_id: str = Field(..., description="ID del hotel")
    room_type_id: str = Field(..., description="ID del tipo de habitación")
    check_in: str = Field(..., description="Fecha de entrada (YYYY-MM-DD)")
    check_out: str = Field(..., description="Fecha de salida (YYYY-MM-DD)")
    guests_count: int = Field(..., description="Número de huéspedes")
    special_requests: Optional[str] = Field(None, description="Solicitudes especiales")

class BookingResponse(BaseModel):
    """
    Modelo para respuestas de reserva
    """
    booking_id: str = Field(..., description="ID único de la reserva")
    hotel_name: str = Field(..., description="Nombre del hotel")
    room_type_name: str = Field(..., description="Nombre del tipo de habitación")
    check_in: datetime = Field(..., description="Fecha y hora de entrada")
    check_out: datetime = Field(..., description="Fecha y hora de salida")
    guests_count: int = Field(..., description="Número de huéspedes")
    status: str = Field(..., description="Estado de la reserva")
    special_requests: Optional[str] = Field(None, description="Solicitudes especiales")
    created_at: datetime = Field(..., description="Fecha y hora de creación de la reserva")

class AvailabilityResponse(BaseModel):
    """
    Modelo para respuestas de disponibilidad
    """
    hotel_name: str = Field(..., description="Nombre del hotel")
    room_types: List[Dict[str, Any]] = Field(..., description="Lista de tipos de habitación con su disponibilidad")
    check_in: str = Field(..., description="Fecha de entrada")
    check_out: str = Field(..., description="Fecha de salida")

class RoomTypeInfo(BaseModel):
    """
    Modelo para información detallada de tipos de habitación
    """
    room_type_id: str = Field(..., description="ID único del tipo de habitación")
    room_type_name: str = Field(..., description="Nombre del tipo de habitación")
    room_type_description: str = Field(..., description="Descripción del tipo de habitación")
    max_occupancy: int = Field(..., description="Ocupación máxima")
    base_price: float = Field(..., description="Precio base por noche")
    amenities: List[str] = Field(..., description="Lista de amenidades")
    available_rooms: int = Field(..., description="Número de habitaciones disponibles")
    total_rooms: int = Field(..., description="Número total de habitaciones")
    gallery: Optional[Dict[str, Any]] = Field(None, description="Galería de imágenes")
    cover_url: Optional[str] = Field(None, description="URL de la imagen principal")

class RoomType(BaseModel):
    """
    Modelo para tipos de habitación
    """
    id: str = Field(..., description="ID único del tipo de habitación")
    name: str = Field(..., description="Nombre del tipo de habitación")
    description: str = Field(..., description="Descripción del tipo de habitación")
    max_occupancy: int = Field(..., description="Ocupación máxima")
    base_price: float = Field(..., description="Precio base por noche")
    amenities: List[str] = Field(..., description="Lista de amenidades disponibles")
    gallery: Optional[List[str]] = Field(None, description="Lista de URLs de imágenes")
    cover_url: Optional[str] = Field(None, description="URL de la imagen principal")

class RoomTypeResponse(BaseModel):
    """
    Modelo para respuesta de consulta de tipos de habitación
    """
    room_types: List[RoomType] = Field(..., description="Lista de tipos de habitación disponibles")
    total_count: int = Field(..., description="Número total de tipos de habitación")