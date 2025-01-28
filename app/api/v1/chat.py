# app/api/v1/chat.py
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import Optional, Dict, Any
from app.models.schemas import Message, BookingRequest, MessageResponse, AvailabilityResponse, BookingResponse, RoomTypeResponse, RoomType
from app.core.chatbot import ChatbotManager

router = APIRouter()

@router.post(
    "/send-message",
    response_model=MessageResponse,
    summary="Enviar mensaje al chatbot",
    description="Procesa un mensaje del usuario y devuelve la respuesta del chatbot utilizando el contexto específico del chatbot_id"
)
async def send_message(
    message: Message = Depends(),
) -> MessageResponse:
    """
    Envía un mensaje al chatbot y recibe una respuesta.

    Args:
        message: Objeto Message que contiene:
            - chatbot_id: ID único del chatbot
            - message: Texto del mensaje del usuario
            - lead_id: ID del usuario o conversación
            - audio_content: Contenido del mensaje de audio en base64 (opcional)

    Returns:
        MessageResponse: Objeto con la respuesta del chatbot

    Raises:
        HTTPException: Error 500 si hay un problema procesando el mensaje
    """
    try:
        print(f"Processing message for chatbot_id: {message.chatbot_id}")
        chatbot = ChatbotManager(message.chatbot_id)
        print(f"ChatbotManager initialized")
        response = await chatbot.process_message(
            message.message,
            message.lead_id,
            message.audio_content
        )
        print(f"Message processed successfully")
        return {"response": response}
    except ValueError as ve:
        print(f"ValueError in send_message: {str(ve)}")
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        print(f"Error in send_message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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