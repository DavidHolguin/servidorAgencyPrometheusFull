from typing import Optional, Dict, Any
from app.models.admin_schemas import AdminChatResponse

class BaseProcessor:
    """Clase base para todos los procesadores"""
    
    def __init__(self):
        self.next_processor = None
        
    def set_next(self, processor: 'BaseProcessor') -> 'BaseProcessor':
        """Establece el siguiente procesador en la cadena"""
        self.next_processor = processor
        return processor
        
    async def process(self, message: str, context: Dict[str, Any]) -> Optional[AdminChatResponse]:
        """
        Procesa un mensaje. Si no puede manejarlo, lo pasa al siguiente procesador.
        
        Args:
            message: Mensaje a procesar
            context: Contexto de la conversación
            
        Returns:
            AdminChatResponse si el mensaje fue procesado, None si debe continuar
        """
        raise NotImplementedError("Los procesadores deben implementar process()")
