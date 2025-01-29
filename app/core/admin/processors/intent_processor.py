from typing import Dict, Any, Optional, Tuple
from app.models.admin_schemas import AdminChatResponse
from app.core.admin.base.base_processor import BaseProcessor

class IntentProcessor(BaseProcessor):
    """Procesa la intención del usuario"""
    
    # Palabras clave para acciones
    CREATE_KEYWORDS = ["crear", "nuevo", "agregar", "añadir"]
    EDIT_KEYWORDS = ["editar", "modificar", "actualizar", "cambiar"]
    DELETE_KEYWORDS = ["eliminar", "borrar", "quitar", "remover"]
    
    # Palabras clave para tipos de activos
    ASSET_KEYWORDS = {
        "chatbot": ["chatbot", "bot", "asistente"],
        "hotel": ["hotel", "alojamiento", "hospedaje"],
        "room_type": ["habitacion", "habitación", "tipo de habitacion", "tipo de habitación", "cuarto"],
        "reservation": ["reserva", "reservación", "booking"],
        "lead": ["lead", "prospecto", "cliente potencial"]
    }
    
    async def process(self, message: str, context: Dict[str, Any]) -> Optional[AdminChatResponse]:
        """Procesa un mensaje para determinar la intención del usuario"""
        
        # Si ya hay un manager activo, pasar al siguiente procesador
        if context.get("current_manager"):
            return await self.next_processor.process(message, context) if self.next_processor else None
            
        # Determinar la operación
        operation = self._determine_operation(message.lower())
        if not operation:
            return await self.next_processor.process(message, context) if self.next_processor else None
            
        asset_type, action = operation
        context["current_operation"] = action
        context["asset_type"] = asset_type
        
        # Dejar que el siguiente procesador maneje la creación del manager
        return await self.next_processor.process(message, context) if self.next_processor else None
        
    def _determine_operation(self, message: str) -> Optional[Tuple[str, str]]:
        """Determina la operación basada en el mensaje"""
        
        # Determinar acción
        action = None
        if any(keyword in message for keyword in self.CREATE_KEYWORDS):
            action = "CREATE"
        elif any(keyword in message for keyword in self.EDIT_KEYWORDS):
            action = "EDIT"
        elif any(keyword in message for keyword in self.DELETE_KEYWORDS):
            action = "DELETE"
            
        # Determinar tipo de activo
        asset_type = None
        for asset, keywords in self.ASSET_KEYWORDS.items():
            if any(keyword in message for keyword in keywords):
                asset_type = asset
                break
                
        if action and asset_type:
            return asset_type, action
            
        return None
