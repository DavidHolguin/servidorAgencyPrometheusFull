# app/api/v1/chat.py
from fastapi import APIRouter, HTTPException, Query, Depends, Path
from typing import Optional
import logging
from datetime import datetime

from app.core.chatbot import ChatbotManager
from app.core.state import get_active_chatbots, active_chatbots
from app.models.schemas import (
    AvailabilityResponse, 
    BookingResponse, 
    BookingRequest,
    RoomTypeResponse,
    RoomType
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/send-message")
async def send_message(
    chatbot_id: str = Query(..., description="ID del chatbot"),
    message: str = Query(..., description="Mensaje del usuario"),
    lead_id: Optional[str] = Query(None, description="ID del lead (opcional)"),
    channel: str = Query("web", description="Canal de comunicación")
):
    """
    Envía un mensaje al chatbot y obtiene una respuesta
    """
    try:
        logger.info(f"Processing message for chatbot_id: {chatbot_id}")
        
        # Obtener o crear instancia del chatbot
        chatbot = active_chatbots.get(chatbot_id)
        
        if not chatbot:
            chatbot = ChatbotManager(chatbot_id)
            await chatbot.initialize()
            active_chatbots[chatbot_id] = chatbot
            logger.info("ChatbotManager initialized")

        # Procesar mensaje
        response_dict = await chatbot.process_message(
            message=message,
            lead_id=lead_id
        )
        
        logger.info(f"Raw response from chatbot: {response_dict}")

        # Formatear respuesta
        formatted_response = {
            "response": response_dict.get("response", "Lo siento, no pude procesar tu mensaje."),
            "suggested_actions": response_dict.get("suggested_actions", []),
            "context": response_dict.get("context", {})
        }
        
        logger.info(f"Formatted response: {formatted_response}")
        return formatted_response

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing message: {str(e)}"
        )

@router.post(
    "/check-availability",
    response_model=AvailabilityResponse,
    summary="Verificar disponibilidad de hotel",
    description="Consulta la disponibilidad de un hotel para las fechas especificadas"
)
async def check_availability(
    hotel_id: str = Query(..., description="ID único del hotel"),
    check_in: str = Query(..., description="Fecha de entrada (formato: YYYY-MM-DD)"),
    check_out: str = Query(..., description="Fecha de salida (formato: YYYY-MM-DD)")
) -> AvailabilityResponse:
    """
    Verifica la disponibilidad de habitaciones en un hotel.

    Args:
        hotel_id: ID único del hotel
        check_in: Fecha de entrada
        check_out: Fecha de salida

    Returns:
        AvailabilityResponse: Objeto con la información de disponibilidad

    Raises:
        HTTPException: Error 500 si hay un problema verificando la disponibilidad
    """
    try:
        chatbot = ChatbotManager(hotel_id)
        availability = await chatbot.check_availability(hotel_id, check_in, check_out)
        return availability
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/create-booking",
    response_model=BookingResponse,
    summary="Crear una nueva reserva",
    description="Crea una nueva reserva en el sistema utilizando los datos proporcionados"
)
async def create_booking(
    booking: BookingRequest = Depends(),
) -> BookingResponse:
    """
    Crea una nueva reserva en el sistema.

    Args:
        booking: Objeto BookingRequest con los detalles de la reserva:
            - agency_id: ID de la agencia
            - hotel_id: ID del hotel
            - check_in: Fecha de entrada
            - check_out: Fecha de salida
            - guest_info: Información del huésped
            - room_type: Tipo de habitación
            - extras: Servicios adicionales (opcional)

    Returns:
        BookingResponse: Objeto con la confirmación de la reserva

    Raises:
        HTTPException: Error 500 si hay un problema creando la reserva
    """
    try:
        chatbot = ChatbotManager(booking.agency_id)
        result = await chatbot.create_booking(booking.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/room-types/{hotel_id}",
    response_model=RoomTypeResponse,
    summary="Obtener tipos de habitación",
    description="Obtiene los tipos de habitación disponibles para un hotel específico"
)
async def get_room_types(
    hotel_id: str = Path(..., description="ID único del hotel"),
    chatbot_id: str = Query(..., description="ID del chatbot para el contexto")
) -> RoomTypeResponse:
    """
    Obtiene los tipos de habitación disponibles para un hotel.

    Args:
        hotel_id: ID único del hotel
        chatbot_id: ID del chatbot para el contexto

    Returns:
        RoomTypeResponse: Lista de tipos de habitación y su cantidad total

    Raises:
        HTTPException: Error 404 si no se encuentra el hotel o 500 si hay un error del servidor
    """
    try:
        chatbot = ChatbotManager(chatbot_id)
        room_types = await chatbot.get_room_types(hotel_id)
        return {
            "room_types": room_types,
            "total_count": len(room_types)
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/room-types/{hotel_id}/{room_type_id}",
    response_model=RoomType,
    summary="Obtener detalles de tipo de habitación",
    description="Obtiene los detalles completos de un tipo de habitación específico"
)
async def get_room_type_details(
    hotel_id: str = Path(..., description="ID único del hotel"),
    room_type_id: str = Path(..., description="ID único del tipo de habitación"),
    chatbot_id: str = Query(..., description="ID del chatbot para el contexto")
) -> RoomType:
    """
    Obtiene los detalles completos de un tipo de habitación específico.

    Args:
        hotel_id: ID único del hotel
        room_type_id: ID único del tipo de habitación
        chatbot_id: ID del chatbot para el contexto

    Returns:
        RoomType: Detalles completos del tipo de habitación

    Raises:
        HTTPException: Error 404 si no se encuentra el tipo de habitación o 500 si hay un error del servidor
    """
    try:
        chatbot = ChatbotManager(chatbot_id)
        room_details = await chatbot.get_room_details(room_type_id)
        if not room_details:
            raise ValueError(f"Room type {room_type_id} not found")
        return room_details
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))