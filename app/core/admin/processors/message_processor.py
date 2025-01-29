from typing import Dict, Any, Optional
from app.models.admin_schemas import AdminChatResponse
from app.core.admin.base.base_processor import BaseProcessor
from app.core.admin.factory.manager_factory import ManagerFactory

class MessageProcessor(BaseProcessor):
    """Procesa mensajes y los dirige al manager apropiado"""
    
    def __init__(self, agency_id: str):
        super().__init__()
        self.agency_id = agency_id
        self.manager_factory = ManagerFactory()
        
    async def process(self, message: str, context: Dict[str, Any]) -> AdminChatResponse:
        """Procesa un mensaje y lo dirige al manager apropiado"""
        
        # Si hay un manager activo
        if context.get("current_manager"):
            if message.lower() in ["cancelar", "cancel", "salir", "exit"]:
                context["current_manager"].reset()
                context["current_manager"] = None
                context["current_operation"] = None
                return AdminChatResponse(
                    message="Operación cancelada. ¿En qué más puedo ayudarte?",
                    action_required=False
                )
                
            response = await context["current_manager"].process_step(
                context["current_manager"].current_step, 
                message
            )
            
            # Si la respuesta no requiere más acciones, limpiar el contexto
            if not response.action_required:
                context["current_manager"] = None
                context["current_operation"] = None
                
            return response
            
        # Si no hay manager activo pero hay una operación pendiente
        if context.get("current_operation") and context.get("asset_type"):
            # Crear el manager apropiado
            manager = self.manager_factory.create_manager(
                context["asset_type"],
                self.agency_id
            )
            
            if not manager:
                return AdminChatResponse(
                    message="Lo siento, no puedo procesar esa operación en este momento."
                )
                
            context["current_manager"] = manager
            return await manager.start_operation(context["current_operation"])
            
        # Si no hay operación ni manager, mostrar ayuda
        return AdminChatResponse(
            message="""No he entendido tu solicitud. Puedo ayudarte con las siguientes operaciones:

1. Chatbots
   - Crear nuevo chatbot
   - Editar chatbot existente
   - Eliminar chatbot

2. Hoteles
   - Crear nuevo hotel
   - Editar hotel existente
   - Eliminar hotel

3. Tipos de Habitación
   - Crear nuevo tipo de habitación
   - Editar tipo de habitación existente
   - Eliminar tipo de habitación

4. Reservas
   - Crear nueva reserva
   - Editar reserva existente
   - Eliminar reserva

5. Leads
   - Crear nuevo lead
   - Editar lead existente
   - Eliminar lead

¿Qué te gustaría hacer?"""
        )
