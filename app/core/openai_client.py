# app/core/openai_client.py
from openai import AsyncOpenAI
import os
import logging
from typing import Optional, Dict, Any, AsyncGenerator
import json
import asyncio
from functools import lru_cache

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=30.0  # Aumentar timeout para mensajes largos
        )
        self.default_config = {
            "model": "gpt-4-turbo-preview",
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
        
    @lru_cache(maxsize=100)
    def _get_cached_system_prompt(self, role: str, context: str) -> str:
        """Cache y retorna el prompt del sistema basado en el rol y contexto"""
        return f"Eres un asistente virtual especializado en {role}. Utiliza este contexto para responder:\n\n{context}"
        
    async def generate_response(
        self,
        messages: list,
        config: Optional[Dict[str, Any]] = None,
        retry_count: int = 2
    ) -> str:
        """
        Genera una respuesta usando la API de OpenAI con reintentos y manejo de errores
        """
        merged_config = {**self.default_config, **(config or {})}
        
        for attempt in range(retry_count):
            try:
                response = await self.client.chat.completions.create(
                    messages=messages,
                    **merged_config
                )
                
                if not response.choices:
                    raise ValueError("No response choices available")
                    
                return response.choices[0].message.content
                
            except Exception as e:
                logger.error(f"Error generating response (attempt {attempt + 1}/{retry_count}): {str(e)}")
                if attempt == retry_count - 1:
                    raise
                await asyncio.sleep(1)  # Esperar antes de reintentar
    
    async def stream_response(
        self,
        messages: list,
        config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Genera una respuesta en streaming para respuestas más rápidas
        """
        merged_config = {**self.default_config, **(config or {})}
        merged_config["stream"] = True
        
        try:
            stream = await self.client.chat.completions.create(
                messages=messages,
                **merged_config
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Error in stream_response: {str(e)}")
            raise

# Instancia global del cliente
openai_client = OpenAIClient()