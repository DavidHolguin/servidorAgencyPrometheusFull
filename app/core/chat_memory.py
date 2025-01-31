from typing import Dict, List, Optional
import json
from datetime import datetime
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_community.vectorstores import FAISS
import numpy as np
import logging

logger = logging.getLogger(__name__)

class EnhancedChatMemory:
    def __init__(self, chatbot_id: str, lead_id: Optional[str] = None):
        self.chatbot_id = chatbot_id
        self.lead_id = lead_id or "default"
        self.session_id = f"{chatbot_id}:{self.lead_id}"
        
        # Configurar LLM para resúmenes
        self.summary_llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0,
            max_tokens=100
        )
        
        # Memoria a corto plazo (últimos mensajes)
        self.short_term_memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="output"
        )
        
        # Memoria a largo plazo (resumen de la conversación)
        self.long_term_memory = ConversationSummaryMemory(
            llm=self.summary_llm,
            memory_key="conversation_summary",
            return_messages=True,
            output_key="output"
        )
        
        # Vector store para búsqueda semántica
        self.vector_store = None
        self.embeddings = OpenAIEmbeddings()
        
    def initialize_vector_store(self, texts: List[str], metadatas: Optional[List[Dict]] = None):
        """Inicializa el vector store con textos y metadatos"""
        try:
            if not texts:
                return
                
            if not metadatas:
                metadatas = [{"type": "system", "created_at": datetime.now().isoformat()} for _ in texts]
                
            self.vector_store = FAISS.from_texts(
                texts,
                self.embeddings,
                metadatas=metadatas
            )
            logger.info(f"Vector store initialized with {len(texts)} texts")
            
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            
    def add_user_message(self, message: str) -> None:
        """Agrega un mensaje del usuario a la memoria"""
        try:
            # Agregar a memoria a corto plazo
            self.short_term_memory.chat_memory.add_message(
                HumanMessage(content=message)
            )
            
            # Agregar a memoria a largo plazo
            self.long_term_memory.chat_memory.add_message(
                HumanMessage(content=message)
            )
            
            # Agregar al vector store si existe
            if self.vector_store:
                self.vector_store.add_texts(
                    [message],
                    metadatas=[{
                        "type": "human",
                        "created_at": datetime.now().isoformat()
                    }]
                )
                
        except Exception as e:
            logger.error(f"Error adding user message: {str(e)}")
            
    def add_ai_message(self, message: str) -> None:
        """Agrega un mensaje del AI a la memoria"""
        try:
            # Agregar a memoria a corto plazo
            self.short_term_memory.chat_memory.add_message(
                AIMessage(content=message)
            )
            
            # Agregar a memoria a largo plazo
            self.long_term_memory.chat_memory.add_message(
                AIMessage(content=message)
            )
            
            # Agregar al vector store si existe
            if self.vector_store:
                self.vector_store.add_texts(
                    [message],
                    metadatas=[{
                        "type": "ai",
                        "created_at": datetime.now().isoformat()
                    }]
                )
                
        except Exception as e:
            logger.error(f"Error adding AI message: {str(e)}")
            
    def get_relevant_history(self, query: str, k: int = 3) -> List[BaseMessage]:
        """Obtiene los mensajes más relevantes de la historia basados en una consulta"""
        try:
            if not self.vector_store:
                return []
                
            # Buscar documentos relevantes
            docs = self.vector_store.similarity_search(query, k=k)
            
            # Convertir documentos a mensajes
            messages = []
            for doc in docs:
                if doc.metadata.get("type") == "human":
                    messages.append(HumanMessage(content=doc.page_content))
                else:
                    messages.append(AIMessage(content=doc.page_content))
                    
            return messages
            
        except Exception as e:
            logger.error(f"Error getting relevant history: {str(e)}")
            return []
            
    def get_context(self, query: str) -> Dict:
        """Obtiene el contexto completo para la generación de respuestas"""
        try:
            # Obtener últimos mensajes
            recent_messages = self.short_term_memory.load_memory_variables({})
            
            # Obtener resumen de la conversación
            conversation_summary = self.long_term_memory.load_memory_variables({})
            
            # Obtener mensajes relevantes
            relevant_messages = self.get_relevant_history(query)
            
            return {
                "recent_messages": recent_messages,
                "conversation_summary": conversation_summary,
                "relevant_messages": relevant_messages
            }
            
        except Exception as e:
            logger.error(f"Error getting context: {str(e)}")
            return {
                "recent_messages": {"chat_history": []},
                "conversation_summary": {},
                "relevant_messages": []
            }
            
    def clear(self) -> None:
        """Limpia toda la memoria"""
        try:
            self.short_term_memory.clear()
            self.long_term_memory.clear()
            if self.vector_store:
                self.vector_store = None
            logger.info("Memory cleared successfully")
            
        except Exception as e:
            logger.error(f"Error clearing memory: {str(e)}")
