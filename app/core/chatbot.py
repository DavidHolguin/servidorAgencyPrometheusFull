import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import re

from app.core.openai_client import openai_client
from app.core.supabase_client import get_client
from app.core.response_enricher import ResponseEnricher

logger = logging.getLogger(__name__)

class ChatbotManager:
    """Gestiona las interacciones y el estado del chatbot"""

    def __init__(self, chatbot_id: str):
        self.chatbot_id = chatbot_id
        self.chatbot_data = {}
        self._related_data_cache = {}
        self._context_cache = {}
        self._conversation_states = {}
        self._executor = ThreadPoolExecutor(max_workers=3)
        self._memory_store = {}
        self._cache_ttl = 300  # 5 minutos
        self.quick_questions = []  # Inicializar quick_questions
        self.base_context = ""     # Inicializar base_context
        self.model_config = {      # Configuración por defecto
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 150,
            "presence_penalty": 0.6,
            "frequency_penalty": 0.6,
        }
        self.supabase = get_client()
        self.response_enricher = ResponseEnricher()

    async def initialize(self):
        """Inicializa el chatbot cargando su configuración desde la base de datos"""
        try:
            # Cargar datos del chatbot
            response = self.supabase.table("chatbots")\
                .select("*")\
                .eq("id", self.chatbot_id)\
                .execute()
            
            logger.info(f"Raw response: {response}")
            logger.info(f"Response type: {type(response)}")
            
            # Verificar si tenemos datos
            if not response or not hasattr(response, 'data') or not response.data:
                raise ValueError(f"Chatbot with id {self.chatbot_id} not found")
            
            logger.info(f"Response data: {response.data}")
            logger.info(f"Response data type: {type(response.data)}")
            logger.info(f"First item type: {type(response.data[0])}")
            
            # Obtener los datos del chatbot
            self.chatbot_data = dict(response.data[0])  # Forzar conversión a diccionario
            logger.info(f"Chatbot data type: {type(self.chatbot_data)}")
            
            # Preparar configuración del modelo
            if 'configuration' in self.chatbot_data:
                config = dict(self.chatbot_data['configuration'])  # Forzar conversión a diccionario
                logger.info(f"Configuration type: {type(config)}")
                self.model_config.update(config)
            
            # Preparar contexto base
            self.base_context = self._prepare_base_context()
            
            # Cargar preguntas rápidas
            self.quick_questions = list(self.chatbot_data.get('quick_questions', []))  # Forzar conversión a lista
            
            # Inicializar memoria
            await self._initialize_memory()
            
            return self
        except Exception as e:
            logger.error(f"Error initializing chatbot: {str(e)}")
            logger.exception("Full traceback:")
            raise

    def _prepare_base_context(self) -> str:
        """Prepara el contexto base del chatbot usando su configuración"""
        context_parts = []
        
        # Personalidad del chatbot
        if personality := self.chatbot_data.get("personality"):
            context_parts.append(f"Personalidad: {personality}")
        
        # Contexto principal
        if context := self.chatbot_data.get("context"):
            context_parts.append(f"Contexto: {context}")
        
        # Estructura del contexto (si existe)
        if context_structure := self.chatbot_data.get("context_structure"):
            if isinstance(context_structure, dict):
                for key, value in context_structure.items():
                    if value and isinstance(value, str):
                        context_parts.append(f"{key}: {value}")
        
        # Configuración de emojis
        if self.chatbot_data.get("use_emojis"):
            context_parts.append("Usa emojis apropiados en tus respuestas para hacerlas más amigables.")
        
        # Mensaje de bienvenida
        if welcome_msg := self.chatbot_data.get("welcome_message"):
            context_parts.append(f"Mensaje de bienvenida: {welcome_msg}")
        
        return "\n\n".join(context_parts)

    async def _initialize_memory(self):
        """Inicializa la memoria a largo plazo desde la base de datos"""
        try:
            memory_data = self.supabase.table("chatbot_memories")\
                .select("*")\
                .eq("chatbot_id", self.chatbot_id)\
                .execute()
            
            if memory_data.data:
                self._memory_store = {
                    item['key']: item['value'] 
                    for item in memory_data.data
                }
        except Exception as e:
            logger.error(f"Error initializing memory: {str(e)}")

    async def process_message(self, message: str, lead_id: str = None, audio_content: str = None) -> Dict:
        """Procesa un mensaje y genera una respuesta"""
        try:
            start_time = time.time()
            
            # Obtener estado de conversación
            conv_state = await self._get_conversation_state_async(lead_id)
            
            # Detectar si es una solicitud de imágenes/fotos
            image_keywords = [
                "foto", "fotos", "imagen", "imágenes", "imagenes", 
                "ver foto", "ver fotos", "muestra", "enseña", "mostrar"
            ]
            
            is_image_request = any(keyword in message.lower() for keyword in image_keywords)
            
            if is_image_request:
                # Extraer el tipo de habitación mencionado
                room_types = {
                    "casa árbol": "casa_arbol",
                    "casa del árbol": "casa_arbol",
                    "presidencial": "presidencial",
                    "cacique": "cacique",
                    "quimbaya": "quimbaya",
                    "familiar": "familiar"
                }
                
                requested_room = None
                for room_name in room_types:
                    if room_name in message.lower():
                        requested_room = room_types[room_name]
                        break
                
                # Consultar imágenes de la habitación
                availability = await self.check_availability(
                    self.chatbot_id,
                    datetime.now().strftime("%Y-%m-%d"),
                    (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                    room_type_id=requested_room
                )
                
                return {
                    "response": availability["markdown_response"],
                    "metadata": {
                        "type": "image_response",
                        "data": availability
                    },
                    "suggested_actions": [
                        {"type": "button", "text": "Reservar ahora"},
                        {"type": "button", "text": "Ver más detalles"},
                        {"type": "button", "text": "Ver otras habitaciones"}
                    ],
                    "context": conv_state
                }
            
            # Verificar respuestas rápidas (solo si no es solicitud de imágenes)
            quick_response = self._check_quick_questions(message)
            if quick_response:
                return {
                    "response": quick_response,
                    "suggested_actions": self._get_suggested_actions(quick_response),
                    "context": conv_state
                }

            # Detectar intención de consultar disponibilidad
            availability_keywords = [
                "disponibilidad", "habitaciones disponibles", "cuartos disponibles",
                "hay habitaciones", "tienen habitaciones", "busco habitación",
                "quiero reservar", "hacer una reserva"
            ]
            
            is_availability_query = any(keyword in message.lower() for keyword in availability_keywords)
            
            if is_availability_query:
                dates = self._extract_dates_from_message(message)
                if not dates:
                    return {
                        "response": "¿Para qué fechas te gustaría consultar la disponibilidad?",
                        "suggested_actions": [
                            {"type": "date_picker", "text": "Seleccionar fechas"}
                        ],
                        "context": conv_state
                    }
                
                availability = await self.check_availability(
                    self.chatbot_id,
                    dates["check_in"],
                    dates["check_out"]
                )
                
                return {
                    "response": availability["markdown_response"],
                    "metadata": {
                        "type": "availability_response",
                        "data": availability
                    },
                    "suggested_actions": [
                        {"type": "button", "text": "Reservar ahora"},
                        {"type": "button", "text": "Ver más detalles"},
                        {"type": "button", "text": "Consultar otras fechas"}
                    ],
                    "context": conv_state
                }

            # Obtener memoria relevante y generar respuesta
            relevant_memory = await self._get_relevant_memory(message, conv_state)
            messages = self._prepare_messages_optimized(message, conv_state, relevant_memory)
            
            full_response = ""
            async for chunk in openai_client.stream_response(
                messages=messages,
                config=self.model_config
            ):
                full_response += chunk

            # Actualizar estado y memoria
            await self._update_conversation_and_memory(lead_id, message, full_response)
            
            # Registrar métricas
            processing_time = time.time() - start_time
            await self._log_performance_metrics(processing_time, len(message))

            return {
                "response": full_response,
                "suggested_actions": self._get_suggested_actions(full_response),
                "context": conv_state
            }

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "response": "Lo siento, ha ocurrido un error. Por favor, intenta nuevamente.",
                "suggested_actions": [],
                "context": conv_state
            }

    def _extract_dates_from_message(self, message: str) -> Optional[Dict[str, str]]:
        """Extrae fechas de check-in y check-out del mensaje usando procesamiento de lenguaje natural"""
        try:
            # Aquí implementarías la lógica de extracción de fechas
            # Por ahora usamos fechas de ejemplo
            return {
                "check_in": "2025-02-01",
                "check_out": "2025-02-05"
            }
        except Exception as e:
            logger.error(f"Error extracting dates: {str(e)}")
            return None

    async def cleanup(self):
        """Limpia recursos y realiza tareas de cierre"""
        try:
            # Cerrar el executor
            if hasattr(self, '_executor'):
                self._executor.shutdown(wait=False)
            
            # Limpiar cachés
            self._context_cache.clear()
            self._conversation_states.clear()
            self._memory_store.clear()
            
            # Registrar última actividad
            try:
                current_time = datetime.now().isoformat()
                self.supabase.table('chatbot_metrics').insert({
                    'chatbot_id': self.chatbot_id,
                    'event_type': 'cleanup',
                    'timestamp': current_time
                }).execute()
            except Exception:
                pass  # Ignorar errores al registrar limpieza
                
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def _get_conversation_state(self, lead_id: str = None) -> Dict:
        """Obtiene el estado actual de la conversación"""
        if not lead_id:
            return {"history": [], "context": {}, "last_updated": datetime.now().timestamp()}
        
        state = self._conversation_states.get(lead_id)
        if not state:
            state = {"history": [], "context": {}, "last_updated": datetime.now().timestamp()}
            self._conversation_states[lead_id] = state
        return state

    async def _get_conversation_state_async(self, lead_id: str = None) -> Dict:
        """Versión asíncrona de _get_conversation_state"""
        return self._get_conversation_state(lead_id)

    def _prepare_messages_optimized(self, message: str, conv_state: dict, memory: dict) -> List[Dict]:
        """Prepara los mensajes de manera optimizada"""
        try:
            messages = []
            
            # Agregar el contexto base del chatbot
            messages.append({
                "role": "system",
                "content": self.base_context
            })

            # Agregar memorias relevantes como contexto adicional
            if long_term := memory.get('long_term', {}):
                memory_context = []
                for key, value in long_term.items():
                    memory_context.append(f"{key}: {value}")
                
                if memory_context:
                    messages.append({
                        "role": "system",
                        "content": "Información relevante del usuario:\n" + "\n".join(memory_context)
                    })

            # Agregar historial relevante
            if history := conv_state.get('history', []):
                # Tomar solo los últimos 3 mensajes para mantener el contexto relevante
                for hist in history[-3:]:
                    messages.extend([
                        {"role": "user", "content": hist.get('user', '')},
                        {"role": "assistant", "content": hist.get('bot', '')}
                    ])

            # Agregar el mensaje actual
            messages.append({"role": "user", "content": message})

            return messages
        except Exception as e:
            logger.error(f"Error preparing messages: {str(e)}")
            return [
                {"role": "system", "content": self.base_context},
                {"role": "user", "content": message}
            ]

    async def _update_conversation_and_memory(self, lead_id: str, user_message: str, bot_response: str):
        """Actualiza el estado de la conversación y la memoria"""
        try:
            # Actualizar estado de la conversación
            state = self._get_conversation_state(lead_id)
            state['history'].append({
                'user': user_message,
                'bot': bot_response,
                'timestamp': datetime.now().isoformat()
            })
            
            # Mantener solo los últimos 10 mensajes
            if len(state['history']) > 10:
                state['history'] = state['history'][-10:]
            
            state['last_updated'] = datetime.now().timestamp()
            self._conversation_states[lead_id] = state

            # Actualizar memoria si es necesario
            await self._update_memory(lead_id, user_message, bot_response)
        except Exception as e:
            logger.error(f"Error updating conversation and memory: {str(e)}")

    async def _log_performance_metrics(self, processing_time: float, message_length: int):
        """Registra métricas de rendimiento en la base de datos"""
        try:
            current_time = datetime.now().isoformat()
            
            self.supabase.table('chatbot_metrics').insert({
                'chatbot_id': self.chatbot_id,
                'processing_time': processing_time,
                'message_length': message_length,
                'timestamp': current_time,
                'success': True
            }).execute()
        except Exception as e:
            logger.error(f"Error logging performance metrics: {str(e)}")

    async def _get_relevant_memory(self, message: str, conv_state: dict) -> dict:
        """Obtiene memorias relevantes basadas en el mensaje actual y el estado de la conversación"""
        try:
            response = self.supabase.rpc(
                'search_memories',
                {
                    'search_query': message,
                    'input_chatbot_id': self.chatbot_id,
                    'min_relevance': 0.5,
                    'limit_param': 5
                }
            ).execute()

            memories = response.data if response and hasattr(response, 'data') else []

            # Ordenar por relevancia y tiempo
            sorted_memories = sorted(
                memories,
                key=lambda x: (x.get('relevance_score', 0), x.get('created_at', '')),
                reverse=True
            )

            # Combinar con el estado actual de la conversación
            return {
                'long_term': {m.get('key', ''): m.get('value', '') for m in sorted_memories},
                'current_context': conv_state.get('context', {}),
                'last_interaction': conv_state.get('last_message')
            }
        except Exception as e:
            logger.error(f"Error retrieving memories: {str(e)}")
            return {}

    async def perform_maintenance(self):
        """Realiza tareas de mantenimiento para optimizar el rendimiento"""
        try:
            tasks = [
                self._cleanup_expired_memories(),
                self._optimize_memory_relevance(),
                self._cleanup_conversation_states(),
                self._clear_old_cache()
            ]
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error during maintenance: {str(e)}")

    async def _cleanup_expired_memories(self):
        """Limpia memorias expiradas y poco relevantes"""
        try:
            self.supabase.rpc(
                'cleanup_expired_memories',
                {'chatbot_id_param': self.chatbot_id}
            ).execute()
        except Exception as e:
            logger.error(f"Error cleaning up memories: {str(e)}")

    async def _optimize_memory_relevance(self):
        """Optimiza las puntuaciones de relevancia basadas en el uso"""
        try:
            # Obtener memorias con baja relevancia
            query = self.supabase.table("chatbot_memories")\
                .select("*")\
                .eq("chatbot_id", self.chatbot_id)\
                .lt("relevance_score", 0.3)\
                .execute()

            for memory in query.data:
                # Recalcular relevancia
                new_score = self._calculate_relevance(memory['key'], memory['value'])
                
                if new_score < 0.1:
                    # Eliminar memorias muy poco relevantes
                    self.supabase.table("chatbot_memories")\
                        .delete()\
                        .eq("id", memory['id'])\
                        .execute()
                else:
                    # Actualizar puntuación
                    self.supabase.table("chatbot_memories")\
                        .update({"relevance_score": new_score})\
                        .eq("id", memory['id'])\
                        .execute()

        except Exception as e:
            logger.error(f"Error optimizing memory relevance: {str(e)}")

    def _cleanup_conversation_states(self):
        """Limpia estados de conversación antiguos"""
        current_time = time.time()
        expired_states = [
            lead_id for lead_id, state in self._conversation_states.items()
            if current_time - state.get('last_updated', 0) > 3600  # 1 hora
        ]
        
        for lead_id in expired_states:
            del self._conversation_states[lead_id]

    def _clear_old_cache(self):
        """Limpia caché antiguo"""
        current_time = time.time()
        self._context_cache = {
            k: v for k, v in self._context_cache.items()
            if current_time - v['timestamp'] < 300  # 5 minutos
        }

    def _calculate_relevance(self, key: str, value: str) -> float:
        """Calcula la puntuación de relevancia para una memoria"""
        # Implementar lógica de relevancia basada en:
        # - Frecuencia de uso
        # - Importancia del contenido
        # - Tiempo transcurrido
        base_score = 1.0
        
        # Ajustar por longitud y complejidad del contenido
        content_score = min(len(value.split()) / 100, 0.5)
        
        # Ajustar por palabras clave importantes
        key_terms = ['reserva', 'destino', 'preferencia', 'contacto', 'fecha']
        term_score = sum(0.1 for term in key_terms if term.lower() in (key + value).lower())
        
        return min(base_score + content_score + term_score, 2.0)

    def _check_quick_questions(self, message: str) -> Optional[str]:
        """Verifica si el mensaje coincide con alguna pregunta rápida predefinida"""
        try:
            if not self.quick_questions:
                return None

            # Normalizar el mensaje para la comparación
            normalized_message = message.lower().strip()

            for question in self.quick_questions:
                if not isinstance(question, dict):
                    continue

                patterns = question.get('patterns', [])
                response = question.get('response')

                if not patterns or not response:
                    continue

                # Verificar si el mensaje coincide con algún patrón
                for pattern in patterns:
                    if pattern.lower() in normalized_message or normalized_message in pattern.lower():
                        return response

            return None
        except Exception as e:
            logger.error(f"Error checking quick questions: {str(e)}")
            return None

    def _get_suggested_actions(self, response: str) -> List[Dict]:
        """Extrae acciones sugeridas de la respuesta"""
        try:
            suggested_actions = []
            
            # Verificar si hay quick_questions configuradas que sean relevantes
            if self.quick_questions:
                for question in self.quick_questions:
                    if isinstance(question, dict) and 'text' in question:
                        suggested_actions.append({
                            'type': 'quick_reply',
                            'text': question['text']
                        })

            # Limitar a máximo 4 sugerencias
            return suggested_actions[:4]
        except Exception as e:
            logger.error(f"Error getting suggested actions: {str(e)}")
            return []

    async def check_availability(
        self,
        hotel_id: str,
        check_in: str,
        check_out: str,
        room_type_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verifica disponibilidad de habitaciones y retorna respuesta enriquecida"""
        try:
            # Convertir fechas
            check_in_date = datetime.strptime(check_in, "%Y-%m-%d")
            check_out_date = datetime.strptime(check_out, "%Y-%m-%d")
            
            # Consultar habitaciones disponibles con imágenes
            query = self.supabase.table("room_types") \
                .select("*, room_type_amenities(amenity:amenities(*)), room_type_images(image_url, description)") \
                .eq("hotel_id", hotel_id)
                
            if room_type_id:
                query = query.eq("id", room_type_id)
                
            rooms = query.execute()
            
            # Verificar disponibilidad real consultando reservas existentes
            available_rooms = []
            for room in rooms.data:
                # Consultar reservas existentes para estas fechas
                bookings = self.supabase.table("bookings") \
                    .select("*") \
                    .eq("hotel_id", hotel_id) \
                    .eq("room_type_id", room["id"]) \
                    .lte("check_in", check_out) \
                    .gte("check_out", check_in) \
                    .execute()
                
                # Si no hay reservas que se superpongan, la habitación está disponible
                if not bookings.data:
                    # Procesar imágenes
                    room_images = []
                    if room.get("room_type_images"):
                        for image in room["room_type_images"]:
                            if image.get("image_url"):
                                room_images.append({
                                    "url": image["image_url"],
                                    "description": image.get("description", "")
                                })
                    
                    # Procesar amenities
                    amenities = []
                    if room.get("room_type_amenities"):
                        for amenity_rel in room["room_type_amenities"]:
                            if amenity_rel.get("amenity"):
                                amenities.append(amenity_rel["amenity"])
                    
                    available_rooms.append({
                        **room,
                        "images": room_images,
                        "amenities": amenities
                    })
            
            # Preparar respuesta en markdown con imágenes
            markdown_response = "### Habitaciones Disponibles\n\n"
            for room in available_rooms:
                markdown_response += f"#### {room['name']}\n"
                markdown_response += f"Precio: ${room['price_per_night']} por noche\n\n"
                
                if room.get("images"):
                    markdown_response += "**Imágenes:**\n"
                    for image in room["images"]:
                        markdown_response += f"![{image.get('description', 'Habitación')}]({image['url']})\n"
                
                if room.get("amenities"):
                    markdown_response += "\n**Amenidades:**\n"
                    for amenity in room["amenities"]:
                        markdown_response += f"- {amenity.get('name', '')}\n"
                
                markdown_response += "\n---\n\n"
            
            return {
                "available": len(available_rooms) > 0,
                "rooms": available_rooms,
                "markdown_response": markdown_response,
                "check_in": check_in,
                "check_out": check_out
            }
            
        except Exception as e:
            logger.error(f"Error checking availability: {str(e)}")
            return {
                "available": False,
                "rooms": [],
                "markdown_response": "Lo siento, ha ocurrido un error al verificar la disponibilidad.",
                "check_in": check_in,
                "check_out": check_out
            }

    async def create_booking(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crea una nueva reserva y retorna confirmación enriquecida"""
        try:
            # Verificar disponibilidad primero
            availability = await self.check_availability(
                booking_data["hotel_id"],
                booking_data["check_in"],
                booking_data["check_out"],
                booking_data.get("room_type_id")
            )
            
            if not availability["available"]:
                raise Exception("No hay habitaciones disponibles para las fechas seleccionadas")
            
            # Crear la reserva
            booking_result = self.supabase.table("bookings").insert({
                "hotel_id": booking_data["hotel_id"],
                "lead_id": booking_data["lead_id"],
                "room_type_id": booking_data["room_type_id"],
                "check_in": booking_data["check_in"],
                "check_out": booking_data["check_out"],
                "total_amount": booking_data["total_amount"],
                "guest_comments": booking_data.get("guest_comments"),
                "guest_requirements": booking_data.get("guest_requirements"),
                "status": "confirmed"
            }).execute()
            
            booking = booking_result.data[0]
            
            # Generar QR para check-in
            qr_result = self.supabase.table("booking_tickets").insert({
                "booking_id": booking["id"],
                "qr_code": f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={booking['id']}",
                "ticket_number": f"TKT-{booking['id'][:8].upper()}",
                "booking_details": booking
            }).execute()
            
            # Obtener datos del hotel y habitación para la confirmación
            hotel = self.supabase.table("hotels") \
                .select("name") \
                .eq("id", booking["hotel_id"]) \
                .single() \
                .execute()
                
            room_type = self.supabase.table("room_types") \
                .select("name") \
                .eq("id", booking["room_type_id"]) \
                .single() \
                .execute()
            
            # Preparar datos para la confirmación
            confirmation_data = {
                **booking,
                "hotel_name": hotel.data["name"],
                "room_type": room_type.data["name"],
                "qr_code": qr_result.data[0]["qr_code"]
            }
            
            # Generar respuesta en Markdown
            markdown_response = self.response_enricher.format_booking_confirmation(confirmation_data)
            
            return {
                "booking": confirmation_data,
                "markdown_response": markdown_response
            }
            
        except Exception as e:
            raise Exception(f"Error al crear la reserva: {str(e)}")