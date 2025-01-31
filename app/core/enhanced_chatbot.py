from typing import Dict, List, Optional, Any
import asyncio
import json
from datetime import datetime
import logging
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.schema import StrOutputParser
from langchain.memory import ConversationBufferMemory
from .chat_memory import EnhancedChatMemory
from .supabase_client import get_client

logger = logging.getLogger(__name__)

class EnhancedChatbotManager:
    def __init__(self, chatbot_id: str):
        self.chatbot_id = chatbot_id
        self.chatbot_data = {}
        self.supabase = get_client()
        self.memory_store = {}
        self.llm = None
        self.chain = None
        
    async def initialize(self):
        """Inicializa el chatbot cargando su configuración y preparando los componentes"""
        try:
            # Cargar datos del chatbot
            response = self.supabase.table('chatbots').select('*').eq('id', self.chatbot_id).execute()
            
            if not response.data or len(response.data) == 0:
                raise ValueError(f"Chatbot with id {self.chatbot_id} not found")
                
            self.chatbot_data = response.data[0]
            
            # Configurar el modelo
            model_config = self.chatbot_data.get('configuration', {})
            self.llm = ChatOpenAI(
                model_name=model_config.get('model', 'gpt-3.5-turbo'),
                temperature=model_config.get('temperature', 0.7),
                streaming=True
            )
            
            # Preparar el prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", self._prepare_system_message()),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}")
            ])
            
            # Crear la cadena
            self.chain = prompt | self.llm | StrOutputParser()
            
            # Cargar memorias relevantes
            await self._load_memories()
            
        except Exception as e:
            logger.error(f"Error initializing chatbot: {str(e)}")
            raise
            
    def _prepare_system_message(self) -> str:
        """Prepara el mensaje del sistema con el contexto y personalidad del chatbot"""
        context_parts = []
        
        # Agregar personalidad
        if personality := self.chatbot_data.get('personality'):
            context_parts.append(f"Personality: {personality}")
            
        # Agregar estructura del contexto
        if context_structure := self.chatbot_data.get('context_structure'):
            if isinstance(context_structure, dict):
                for key, value in context_structure.items():
                    if value and isinstance(value, str):
                        context_parts.append(f"{key}: {value}")
                        
        # Agregar contexto adicional
        if context := self.chatbot_data.get('context'):
            context_parts.append(f"Additional Context: {context}")
            
        return "\n".join(context_parts)
        
    async def _load_memories(self):
        """Carga las memorias relevantes desde Supabase"""
        try:
            response = self.supabase.table('chatbot_memories').select('*').eq('chatbot_id', self.chatbot_id).execute()
            
            if response.data:
                texts = []
                metadatas = []
                for memory in response.data:
                    texts.append(memory['content'])
                    metadatas.append({
                        'type': memory['type'],
                        'created_at': memory['created_at']
                    })
                    
                # Inicializar vector store con las memorias
                memory = self._get_memory()
                memory.initialize_vector_store(texts, metadatas)
                
        except Exception as e:
            logger.error(f"Error loading memories: {str(e)}")
            
    def _get_memory(self, lead_id: Optional[str] = None) -> EnhancedChatMemory:
        """Obtiene o crea una instancia de memoria para un lead"""
        key = f"{self.chatbot_id}:{lead_id or 'default'}"
        if key not in self.memory_store:
            self.memory_store[key] = EnhancedChatMemory(self.chatbot_id, lead_id)
        return self.memory_store[key]
        
    async def process_message(self, message: str, lead_id: Optional[str] = None) -> Dict[str, Any]:
        """Procesa un mensaje y genera una respuesta"""
        try:
            if not self.chain:
                await self.initialize()
                
            # Obtener memoria
            memory = self._get_memory(lead_id)
            
            # Obtener contexto relevante
            context = memory.get_context(message)
            
            # Preparar el historial de chat para LangChain
            chat_history = []
            for msg in context['recent_messages'].get('chat_history', []):
                chat_history.append(msg)
            
            # Generar respuesta
            response = await self.chain.ainvoke({
                "input": message,
                "chat_history": chat_history
            })
            
            # Actualizar memoria
            memory.add_user_message(message)
            memory.add_ai_message(response)
            
            # Extraer acciones sugeridas
            suggested_actions = self._get_suggested_actions(response)
            
            return {
                "response": response,
                "suggested_actions": suggested_actions,
                "context": {
                    "history": chat_history,
                    "context": context.get('conversation_summary', {}),
                    "last_updated": datetime.now().timestamp()
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "response": "Lo siento, ha ocurrido un error al generar la respuesta.",
                "suggested_actions": [],
                "context": {
                    "history": [],
                    "context": {},
                    "last_updated": datetime.now().timestamp()
                }
            }
            
    def _get_suggested_actions(self, response: str) -> List[str]:
        """Extrae acciones sugeridas de la respuesta"""
        # Por ahora retornamos las quick_questions si existen
        return self.chatbot_data.get('quick_questions', [])
