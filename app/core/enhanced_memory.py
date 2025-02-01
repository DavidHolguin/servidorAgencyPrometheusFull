from typing import Dict, Any, List
import logging
from langchain.memory import ConversationBufferMemory

logger = logging.getLogger(__name__)

class EnhancedChatMemory:
    """Gestiona la memoria del chatbot"""
    
    def __init__(self, chatbot_id: str):
        """
        Inicializa la memoria del chatbot
        
        Args:
            chatbot_id: ID del chatbot
        """
        self.chatbot_id = chatbot_id
        self.short_term_memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
    async def cleanup(self):
        """Limpia la memoria del chatbot"""
        try:
            self.short_term_memory.clear()
        except Exception as e:
            logger.error(f"Error limpiando memoria: {str(e)}")
            raise
