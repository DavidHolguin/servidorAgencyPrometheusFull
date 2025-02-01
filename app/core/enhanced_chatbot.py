from typing import Dict, Any, Optional, List
import logging
from app.core.enhanced_chatbot_base import EnhancedChatbotBase
from app.core.gallery_manager import GalleryManager
from app.core.response_enricher import ResponseEnricher
from app.core.enhanced_memory import EnhancedChatMemory
from app.core.cache_manager import CacheManager
from app.core.supabase_client import get_client

logger = logging.getLogger(__name__)

class EnhancedChatbotManager:
    def __init__(self):
        self.active_chatbots: Dict[str, EnhancedChatbotBase] = {}
        self.supabase = get_client()
        
    async def get_or_create_chatbot(self, chatbot_id: str) -> EnhancedChatbotBase:
        """Obtiene o crea una instancia de chatbot"""
        if chatbot_id not in self.active_chatbots:
            # Verificar que el chatbot existe en Supabase
            response = self.supabase.table('chatbots')\
                .select('*')\
                .eq('id', chatbot_id)\
                .execute()
                
            if not response.data:
                raise ValueError(f"No se encontró el chatbot con ID {chatbot_id}")
                
            # Crear y configurar el chatbot
            chatbot = EnhancedChatbot(None, chatbot_id)
            await chatbot.initialize()
            self.active_chatbots[chatbot_id] = chatbot
            
        return self.active_chatbots[chatbot_id]
        
    async def cleanup(self, chatbot_id: Optional[str] = None):
        """Limpia los recursos de un chatbot específico o todos los chatbots"""
        if chatbot_id:
            if chatbot_id in self.active_chatbots:
                await self.active_chatbots[chatbot_id].cleanup()
                del self.active_chatbots[chatbot_id]
        else:
            for bot in list(self.active_chatbots.values()):
                await bot.cleanup()
            self.active_chatbots.clear()


class EnhancedChatbot(EnhancedChatbotBase):
    """Chatbot mejorado con capacidades multimedia"""
    
    def __init__(self, agency_id: str, chatbot_id: str):
        """
        Inicializa el chatbot mejorado
        
        Args:
            agency_id: ID de la agencia
            chatbot_id: ID del chatbot
        """
        super().__init__(agency_id, chatbot_id)
        self.response_enricher = ResponseEnricher()
        self.memory = None
        self.cache_manager = None
        self.gallery_manager = GalleryManager()
        
    async def initialize(self):
        """Inicializa el chatbot y sus componentes"""
        # Inicializar clase base
        await super().initialize()
        
        # Inicializar GalleryManager
        await self.gallery_manager.initialize()
        
    async def process_message(self, message: str, chatbot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un mensaje del usuario y genera una respuesta enriquecida
        
        Args:
            message: Mensaje del usuario
            chatbot_data: Datos del chatbot
            
        Returns:
            Dict[str, Any]: Respuesta enriquecida con contenido multimedia
        """
        try:
            # Actualizar datos del chatbot
            self.chatbot_data = chatbot_data
            
            # Obtener respuesta del LLM usando el método de la clase base
            llm_response = await super().process_message(message)
            
            # Extraer términos de búsqueda del mensaje
            search_terms = self.gallery_manager.extract_search_terms(message)
            
            # Enriquecer respuesta con contenido multimedia
            enriched_response = await self.response_enricher.enrich_response(
                llm_response=llm_response,
                search_terms=search_terms
            )
            
            return enriched_response
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            raise