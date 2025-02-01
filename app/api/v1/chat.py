# app/api/v1/chat.py
from fastapi import APIRouter, HTTPException, Query, Depends, Path
from typing import Optional
import logging
from datetime import datetime
from app.core.enhanced_chatbot import EnhancedChatbot

from app.core import EnhancedChatbotManager
from app.core.supabase_client import get_client
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

# Diccionario para mantener las instancias de chatbots
chatbot_instances = {}

async def get_or_create_chatbot(agency_id: str, chatbot_id: str) -> EnhancedChatbot:
    """
    Obtiene o crea una instancia de chatbot
    
    Args:
        agency_id: ID de la agencia
        chatbot_id: ID del chatbot
        
    Returns:
        EnhancedChatbot: Instancia del chatbot
    """
    chatbot_key = f"{agency_id}:{chatbot_id}"
    
    if chatbot_key not in chatbot_instances:
        # Crear nueva instancia
        chatbot = EnhancedChatbot(agency_id=agency_id, chatbot_id=chatbot_id)
        # Inicializar el chatbot
        await chatbot.initialize()
        chatbot_instances[chatbot_key] = chatbot
        logger.info(f"Nuevo chatbot creado: {chatbot_key}")
    
    return chatbot_instances[chatbot_key]

@router.post("/send-message")
@router.get("/send-message")
async def send_message(
    agency_id: str = Query(..., description="ID de la agencia"),
    chatbot_id: str = Query(..., description="ID del chatbot"),
    message: str = Query(..., description="Mensaje del usuario"),
    lead_id: Optional[str] = Query(None, description="ID del lead (opcional)"),
    channel: str = Query("web", description="Canal de comunicación")
):
    """
    Envía un mensaje al chatbot y obtiene una respuesta
    
    Args:
        agency_id: ID de la agencia propietaria del chatbot
        chatbot_id: ID del chatbot a utilizar
        message: Mensaje del usuario
        lead_id: ID opcional del lead/usuario
        channel: Canal de comunicación (web, whatsapp, etc.)
        
    Returns:
        Dict con la respuesta del chatbot y metadatos
        
    Raises:
        HTTPException: 
            - 404 si el chatbot no existe o no pertenece a la agencia
            - 500 si hay un error procesando el mensaje
    """
    try:
        # Validar que el chatbot pertenece a la agencia
        supabase = get_client()
        chatbot_response = supabase.table('chatbots')\
            .select('*')\
            .eq('id', chatbot_id)\
            .eq('agency_id', agency_id)\
            .execute()
            
        if not chatbot_response.data:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró el chatbot {chatbot_id} para la agencia {agency_id}"
            )
            
        # Obtener o crear instancia del chatbot
        chatbot = await get_or_create_chatbot(agency_id, chatbot_id)
        
        # Procesar mensaje
        response = await chatbot.process_message(
            message=message,
            chatbot_data=chatbot_response.data[0]
        )
        
        return {
            "text": response["text"],
            "galleries": response.get("galleries", []),
            "timestamp": datetime.now().isoformat(),
            "chatbot_id": chatbot_id,
            "agency_id": agency_id,
            "lead_id": lead_id,
            "channel": channel
        }
    except HTTPException as he:
        # Re-lanzar excepciones HTTP
        raise he
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando el mensaje: {str(e)}"
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
        chatbot = await get_or_create_chatbot(hotel_id, hotel_id)
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
        chatbot = await get_or_create_chatbot(booking.agency_id, booking.agency_id)
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
        chatbot = await get_or_create_chatbot(chatbot_id, chatbot_id)
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
        chatbot = await get_or_create_chatbot(chatbot_id, chatbot_id)
        room_details = await chatbot.get_room_details(room_type_id)
        if not room_details:
            raise ValueError(f"Room type {room_type_id} not found")
        return room_details
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))