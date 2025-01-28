from fastapi import APIRouter, Depends, HTTPException
from app.models.admin_schemas import AdminChatRequest, AdminChatResponse
from app.core.admin_chatbot import AdminChatbotManager
from typing import Dict

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post(
    "/chat",
    response_model=AdminChatResponse,
    summary="Procesar mensaje del administrador",
    description="Procesa un mensaje del administrador y retorna una respuesta enriquecida con componentes UI"
)
async def process_admin_message(
    request: AdminChatRequest
) -> AdminChatResponse:
    """
    Endpoint para procesar mensajes del administrador.

    Este endpoint maneja la comunicación con el chatbot administrativo, que puede:
    - Crear y gestionar hoteles
    - Crear y gestionar tipos de habitaciones
    - Gestionar reservas
    - Configurar chatbots
    - Y otras tareas administrativas

    La respuesta puede incluir:
    - Mensaje en lenguaje natural
    - Componentes UI para recolectar información
    - Solicitudes de confirmación
    - Contexto adicional

    Args:
        request: AdminChatRequest con el mensaje y contexto del administrador

    Returns:
        AdminChatResponse con la respuesta enriquecida del chatbot

    Raises:
        HTTPException: Si hay un error procesando el mensaje
    """
    try:
        # Inicializar el chatbot administrativo
        chatbot = AdminChatbotManager(
            agency_id=request.agency_id,
            user_id=request.user_id
        )

        # Procesar el mensaje
        response = await chatbot.process_message(
            message=request.message
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/execute-action",
    response_model=Dict,
    summary="Ejecutar acción administrativa",
    description="Ejecuta una acción administrativa confirmada por el usuario"
)
async def execute_admin_action(
    action_data: Dict
) -> Dict:
    """
    Ejecuta una acción administrativa después de la confirmación del usuario.

    Args:
        action_data: Datos de la acción a ejecutar

    Returns:
        Dict con el resultado de la acción

    Raises:
        HTTPException: Si hay un error ejecutando la acción
    """
    try:
        # Aquí implementaremos la lógica para ejecutar las acciones
        # como crear hoteles, tipos de habitaciones, etc.
        return {"status": "success", "message": "Acción ejecutada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
