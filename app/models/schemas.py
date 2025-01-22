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
    lead_id: str = Field(..., description="ID único del cliente potencial")
    agency_id: str = Field(..., description="ID de la agencia que procesa la reserva")
    booking_type: str = Field(..., description="Tipo de reserva (hotel, tour, paquete)")
    items: List[BookingItem] = Field(..., description="Items incluidos en la reserva")
    guest_info: GuestInfo = Field(..., description="Información del huésped principal")
    check_in: Optional[datetime] = Field(None, description="Fecha y hora de entrada")
    check_out: Optional[datetime] = Field(None, description="Fecha y hora de salida")
    special_requests: Optional[str] = Field(None, description="Solicitudes especiales")

class AvailabilityResponse(BaseModel):
    """
    Modelo para respuestas de disponibilidad
    """
    available: bool = Field(..., description="Indica si hay disponibilidad")
    rooms_available: int = Field(..., description="Número de habitaciones/items disponibles")
    price_range: Dict[str, float] = Field(
        ...,
        description="Rango de precios disponibles (min y max)"
    )
    alternatives: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Alternativas disponibles si no hay disponibilidad en las fechas solicitadas"
    )

class BookingResponse(BaseModel):
    """
    Modelo para respuestas de creación de reserva
    """
    booking_id: str = Field(..., description="ID único de la reserva creada")
    status: str = Field(..., description="Estado de la reserva")
    total_amount: float = Field(..., description="Monto total de la reserva")
    confirmation_code: str = Field(..., description="Código de confirmación")
    payment_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Información de pago si aplica"
    )
    booking_details: Dict[str, Any] = Field(
        ...,
        description="Detalles completos de la reserva"
    )