# app/core/openai_client.py
from openai import AsyncOpenAI
import os
import logging
from typing import Optional, Dict, Any, AsyncGenerator
import json
import asyncio
from functools import lru_cache
import time

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=30.0
        )
        self.default_config = {
            "model": "gpt-4-turbo-preview",
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
        self._response_cache = {}
        
        # Lista de parámetros válidos para la API de OpenAI
        self.valid_params = {
            "model",
            "temperature",
            "max_tokens",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "stream",
            "stop",
            "n",
            "logit_bias",
            "user",
            "response_format",
            "seed"
        }
        
    def _filter_config(self, config: dict) -> dict:
        """Filtra la configuración para incluir solo parámetros válidos de OpenAI"""
        return {k: v for k, v in config.items() if k in self.valid_params}
        
    def _get_cache_key(self, messages: list, config: dict) -> str:
        """Genera una clave única para el caché basada en los mensajes y configuración"""
        messages_str = json.dumps(messages, sort_keys=True)
        config_str = json.dumps(config, sort_keys=True)
        return f"{messages_str}:{config_str}"
        
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Obtiene una respuesta cacheada si está disponible y válida"""
        if cache_key in self._response_cache:
            cache_entry = self._response_cache[cache_key]
            if time.time() - cache_entry['timestamp'] < 300:  # 5 minutos de validez
                return cache_entry['response']
        return None
        
    async def generate_response(
        self,
        messages: list,
        config: Optional[Dict[str, Any]] = None,
        retry_count: int = 2,
        use_cache: bool = True
    ) -> str:
        """
        Genera una respuesta usando la API de OpenAI con reintentos, caché y manejo de errores
        """
        try:
            # Combinar configuración predeterminada con la configuración proporcionada
            final_config = self.default_config.copy()
            if config:
                final_config.update(config)
                
            # Filtrar solo los parámetros válidos
            final_config = self._filter_config(final_config)
            
            # Verificar caché si está habilitado
            if use_cache:
                cache_key = self._get_cache_key(messages, final_config)
                cached_response = self._get_cached_response(cache_key)
                if cached_response:
                    return cached_response
            
            # Realizar llamada a la API con reintentos
            for attempt in range(retry_count + 1):
                try:
                    response = await self.client.chat.completions.create(
                        messages=messages,
                        **final_config
                    )
                    
                    result = response.choices[0].message.content
                    
                    # Guardar en caché si está habilitado
                    if use_cache:
                        self._response_cache[cache_key] = {
                            'response': result,
                            'timestamp': time.time()
                        }
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Error in attempt {attempt + 1}: {str(e)}")
                    if attempt == retry_count:
                        raise
                    await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise
            
    def _optimize_messages(self, messages: list) -> list:
        """Optimiza los mensajes para reducir tokens y mejorar el contexto"""
        optimized = []
        total_length = 0
        max_length = 4000  # Límite aproximado de tokens
        
        # Mantener siempre el mensaje del sistema y el último mensaje del usuario
        system_message = next((m for m in messages if m['role'] == 'system'), None)
        last_user_message = next((m for m in reversed(messages) if m['role'] == 'user'), None)
        
        if system_message:
            optimized.append(system_message)
            total_length += len(system_message['content'])
        
        # Filtrar mensajes relevantes del historial
        history_messages = [
            m for m in messages 
            if m['role'] != 'system' and m != last_user_message
        ]
        
        # Priorizar mensajes más recientes y relevantes
        for msg in reversed(history_messages):
            msg_length = len(msg['content'])
            if total_length + msg_length < max_length:
                optimized.append(msg)
                total_length += msg_length
            else:
                break
        
        if last_user_message:
            optimized.append(last_user_message)
        
        return optimized
    
    async def stream_response(
        self,
        messages: list,
        config: Optional[Dict[str, Any]] = None,
        retry_count: int = 2
    ) -> AsyncGenerator[str, None]:
        """
        Genera una respuesta usando la API de OpenAI de manera streaming
        
        Args:
            messages: Lista de mensajes para el modelo
            config: Configuración opcional para la llamada a la API
            retry_count: Número de reintentos en caso de error
            
        Yields:
            Chunks de texto de la respuesta
        """
        # Combinar configuración por defecto con la proporcionada
        final_config = self.default_config.copy()
        if config:
            final_config.update(config)
            
        # Filtrar solo los parámetros válidos
        final_config = self._filter_config(final_config)
            
        # Asegurarse de que stream está habilitado
        final_config["stream"] = True
            
        for attempt in range(retry_count + 1):
            try:
                stream = await self.client.chat.completions.create(
                    messages=messages,
                    **final_config
                )
                
                async for chunk in stream:
                    if chunk.choices[0].finish_reason is not None:
                        break
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
                        
                break  # Si llegamos aquí, todo salió bien
                
            except Exception as e:
                logger.error(f"Error in stream_response (attempt {attempt + 1}): {str(e)}")
                if attempt == retry_count:  # Si es el último intento
                    raise
                await asyncio.sleep(1)  # Esperar antes de reintentar

# Instancia global del cliente
openai_client = OpenAIClient()