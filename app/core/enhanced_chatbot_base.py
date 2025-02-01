from typing import Dict, Any, Optional
import logging
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.callbacks import StreamingStdOutCallbackHandler

from app.core.response_enricher import ResponseEnricher
from app.core.enhanced_memory import EnhancedChatMemory
from app.core.cache_manager import CacheManager
from app.core.supabase_client import get_client

logger = logging.getLogger(__name__)

class EnhancedChatbotBase:
    """Clase base para el chatbot mejorado"""
    
    def __init__(self, agency_id: str, chatbot_id: str):
        """
        Inicializa el chatbot base
        
        Args:
            agency_id: ID de la agencia
            chatbot_id: ID del chatbot
        """
        self.agency_id = agency_id
        self.chatbot_id = chatbot_id
        self.supabase = get_client()
        self.response_enricher = None
        self.memory = None
        self.cache_manager = None
        self.llm_chain = None
        self.chatbot_data = None
        
    async def load_chatbot_data(self):
        """Carga los datos del chatbot desde Supabase"""
        try:
            response = self.supabase.table('chatbots')\
                .select('*')\
                .eq('id', self.chatbot_id)\
                .execute()
                
            if not response.data:
                raise ValueError(f"No se encontró el chatbot con ID {self.chatbot_id}")
                
            self.chatbot_data = response.data[0]
            
        except Exception as e:
            logger.error(f"Error cargando datos del chatbot: {str(e)}")
            raise
            
    async def initialize(self):
        """Inicializa el chatbot y sus componentes"""
        try:
            # Cargar datos del chatbot
            await self.load_chatbot_data()
            
            # Inicializar componentes
            self.memory = EnhancedChatMemory(chatbot_id=self.chatbot_id)
            self.response_enricher = ResponseEnricher()
            self.cache_manager = CacheManager()
            
            # Inicializar el ResponseEnricher
            await self.response_enricher.initialize()
            
            # Configurar LLM y cadena
            llm = ChatOpenAI(
                temperature=0.7,
                streaming=True,
                callbacks=[StreamingStdOutCallbackHandler()]
            )
            
            # Construir el prompt con la información del chatbot
            system_prompt = f"""
            {self.chatbot_data['context']}
            
            Tu personalidad: {self.chatbot_data['personality']}
            
            Tienes acceso a una galería de imágenes que puedes mostrar a los usuarios. Cuando el usuario pregunte por fotos o imágenes, o cuando sea relevante mostrar contenido visual, SIEMPRE debes responder asumiendo que las imágenes estarán disponibles. NUNCA digas que no puedes mostrar imágenes.

            Reglas adicionales:
            - {'Usa emojis en tus respuestas cuando sea apropiado.' if self.chatbot_data['use_emojis'] else 'No uses emojis en tus respuestas.'}
            - Mantén un tono amigable y profesional.
            - Cuando muestres imágenes, describe brevemente lo que el usuario podrá ver en ellas.
            - Si el usuario pregunta por más imágenes, indícale que puede solicitarlas.
            """
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}")
            ])
            
            self.llm_chain = LLMChain(
                llm=llm,
                prompt=prompt,
                memory=self.memory.short_term_memory,
                verbose=True
            )
            
        except Exception as e:
            logger.error(f"Error inicializando chatbot: {str(e)}")
            raise
        
    async def process_message(self, message: str) -> str:
        """
        Procesa un mensaje y retorna la respuesta
        
        Args:
            message: Mensaje del usuario
            
        Returns:
            str: Texto de la respuesta del LLM
        """
        try:
            # Obtener respuesta del LLM
            chain_response = await self.llm_chain.arun(input=message)
            return chain_response
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            return "Lo siento, hubo un error procesando tu mensaje. Por favor, intenta de nuevo."

    async def cleanup(self):
        """Limpieza de recursos"""
        if self.memory:
            await self.memory.cleanup()
