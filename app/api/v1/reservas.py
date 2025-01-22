from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from app.models.schemas import BookingRequest, BookingResponse, AvailabilityResponse
from app.core.chatbot import ChatbotManager

router = APIRouter()

@router.get(
    "/availability/{hotel_id}",
    response_model=AvailabilityResponse,
    summary="Consultar disponibilidad de hotel",
    description="Verifica la disponibilidad de habitaciones en un hotel para las fechas especificadas"
)
async def get_availability(
    hotel_id: str,
    check_in: str,
    check_out: str,
    room_type: Optional[str] = None
) -> AvailabilityResponse:
    """
    Endpoint para consultar disponibilidad de habitaciones.

    Args:
        hotel_id: ID único del hotel
        check_in: Fecha de entrada (YYYY-MM-DD)
        check_out: Fecha de salida (YYYY-MM-DD)
        room_type: Tipo de habitación (opcional)

    Returns:
        AvailabilityResponse con la información de disponibilidad
    """
    try:
        chatbot = ChatbotManager(hotel_id)
        availability = await chatbot.check_availability(
            hotel_id,
            check_in,
            check_out,
            room_type
        )
        return availability
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/bookings",
    response_model=BookingResponse,
    summary="Crear nueva reserva",
    description="Crea una nueva reserva en el sistema"
)
async def create_booking(booking: BookingRequest) -> BookingResponse:
    """
    Endpoint para crear una nueva reserva.

    Args:
        booking: Datos de la reserva incluyendo información del huésped y detalles de la reserva

    Returns:
        BookingResponse con la confirmación de la reserva
    """
    try:
        chatbot = ChatbotManager(booking.agency_id)
        result = await chatbot.create_booking(booking.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/bookings/{booking_id}",
    response_model=BookingResponse,
    summary="Obtener detalles de reserva",
    description="Obtiene los detalles de una reserva específica"
)
async def get_booking(booking_id: str) -> BookingResponse:
    """
    Endpoint para obtener detalles de una reserva.

    Args:
        booking_id: ID único de la reserva

    Returns:
        BookingResponse con los detalles de la reserva
    """
    try:
        # Aquí deberías obtener la agency_id basada en el booking_id
        agency_id = "default_agency"  # Esto debe ser implementado
        chatbot = ChatbotManager(agency_id)
        booking = await chatbot.get_booking(booking_id)
        return booking
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
