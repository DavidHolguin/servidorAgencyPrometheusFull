from typing import Dict, Optional, List, Any
import os
from openai import AsyncOpenAI
from app.core.supabase import supabase
from app.core.openai_client import openai_client
import json
import time
from functools import lru_cache
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

class ChatbotManager:
    def __init__(self, chatbot_id: str):
        self.chatbot_id = chatbot_id
        self.chatbot_data = {}
        self._related_data_cache = {}
        self._context_cache = {}
        self._conversation_states = {}
        self._executor = ThreadPoolExecutor(max_workers=3)
        
    async def initialize(self):
        """Inicializa el chatbot de manera asíncrona"""
        try:
            self.chatbot_data = await asyncio.get_event_loop().run_in_executor(
                self._executor, 
                self._load_chatbot_data
            )
            return self
        except Exception as e:
            logger.error(f"Error initializing chatbot: {str(e)}")
            raise

    @lru_cache(maxsize=1)
    def _get_personality_config(self) -> Dict:
        """Obtiene y cachea la configuración de personalidad"""
        personality = self.chatbot_data.get('personality', {})
        if isinstance(personality, str):
            try:
                personality = json.loads(personality)
            except:
                personality = {}
        return personality

    def _get_cached_context(self, cache_key: str) -> Optional[str]:
        """Obtiene contexto cacheado si está disponible y válido"""
        if cache_key in self._context_cache:
            cache_entry = self._context_cache[cache_key]
            if time.time() - cache_entry['timestamp'] < 300:  # 5 minutos
                return cache_entry['context']
        return None

    async def process_message(self, message: str, lead_id: str = None, audio_content: str = None) -> Dict:
        """Procesa un mensaje y retorna la respuesta de manera optimizada"""
        try:
            # Obtener o crear estado de conversación
            conv_state = self._get_conversation_state(lead_id)
            
            # Construir contexto de manera eficiente
            cache_key = f"context_{self.chatbot_id}"
            context = self._get_cached_context(cache_key)
            
            if not context:
                context = await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    self._build_context
                )
                self._context_cache[cache_key] = {
                    'context': context,
                    'timestamp': time.time()
                }
            
            # Preparar mensajes para OpenAI de manera eficiente
            messages = await self._prepare_messages_async(message, context, conv_state)
            
            # Obtener configuración del modelo
            model_config = self._get_model_config()
            
            # Generar respuesta usando streaming para mejor rendimiento
            response_chunks = []
            async for chunk in openai_client.stream_response(
                messages=messages,
                config=model_config
            ):
                response_chunks.append(chunk)
            
            response = "".join(response_chunks)
            
            # Actualizar estado de conversación
            self._update_conversation_state(lead_id, message, response)
            
            # Procesar acciones sugeridas de manera asíncrona
            suggested_actions = await self._get_suggested_actions(response)
            
            return {
                "response": response,
                "suggested_actions": suggested_actions,
                "context": conv_state
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "response": "Lo siento, ha ocurrido un error al procesar tu mensaje. Por favor, intenta nuevamente.",
                "suggested_actions": [],
                "context": {}
            }

    async def _prepare_messages_async(self, user_message: str, context: str, conv_state: Dict) -> List[Dict]:
        """Prepara los mensajes para OpenAI de manera asíncrona"""
        try:
            personality = self._get_personality_config()
            
            # Construir el mensaje del sistema
            system_message = {
                "role": "system",
                "content": await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    self._build_system_message,
                    personality,
                    context
                )
            }
            
            messages = [system_message]
            
            # Añadir historial relevante
            if conv_history := conv_state.get('history', []):
                # Usar solo los últimos 5 mensajes más relevantes
                for msg in conv_history[-5:]:
                    messages.append({
                        "role": "user" if msg['type'] == 'user' else "assistant",
                        "content": msg['content']
                    })
            
            # Añadir mensaje actual
            messages.append({"role": "user", "content": user_message})
            
            return messages
            
        except Exception as e:
            logger.error(f"Error preparing messages: {str(e)}")
            return [
                {"role": "system", "content": context},
                {"role": "user", "content": user_message}
            ]

    def _build_system_message(self, personality: Dict, context: str) -> str:
        """Construye el mensaje del sistema de manera eficiente"""
        return f"""Eres un asistente virtual especializado en el Parque Temático Los Quimbayas.
        
        Personalidad:
        - Tono: {personality.get('tone', 'profesional')}
        - Nivel de formalidad: {personality.get('formality_level', 'semiformal')}
        - Uso de emojis: {personality.get('emoji_usage', 'moderado')}
        - Estilo de lenguaje: {personality.get('language_style', 'claro y conciso')}
        
        Contexto:
        {context}
        
        Instrucciones:
        1. Sé conciso y directo
        2. Usa emojis moderadamente
        3. Prioriza información relevante
        4. Indica si no estás seguro
        5. Mantén un tono profesional pero amigable
        6. Responde en español
        """

    async def _get_suggested_actions(self, response: str) -> List[str]:
        """Obtiene acciones sugeridas de manera asíncrona"""
        try:
            quick_questions = self.chatbot_data.get('quick_questions', [])
            if not quick_questions:
                return []
                
            # Seleccionar preguntas relevantes basadas en el contexto
            relevant_questions = []
            for q in quick_questions:
                if len(relevant_questions) >= 3:
                    break
                if any(keyword in response.lower() for keyword in q.lower().split()):
                    relevant_questions.append(q)
            
            return relevant_questions or quick_questions[:3]
            
        except Exception as e:
            logger.error(f"Error getting suggested actions: {str(e)}")
            return []

    def _load_chatbot_data(self) -> Dict:
        """Carga la información del chatbot desde Supabase de manera optimizada"""
        try:
            if not supabase:
                raise ValueError("Supabase client is not initialized")
            
            # Realizar una única consulta con todas las relaciones necesarias
            response = supabase.table("chatbots")\
                .select(
                    "*," 
                    "agency:agencies(id, name, description, contact_info),"
                    "landing_page:landing_pages(id, title, description),"
                    "hotels:hotels(id, name, description, amenities, base_price, room_types(*))"
                )\
                .eq("id", self.chatbot_id)\
                .execute()
                
            if not response.data:
                raise ValueError(f"No chatbot found with id {self.chatbot_id}")
            
            chatbot_data = response.data[0]
            logger.debug(f"Raw chatbot data loaded for {self.chatbot_id}")
            
            # Procesar y estructurar los datos
            processed_data = {
                "id": str(chatbot_data.get("id", self.chatbot_id)),
                "name": str(chatbot_data.get("name", "Assistant")),
                "description": str(chatbot_data.get("description", "")),
                "agency_id": str(chatbot_data.get("agency_id", "")),
                "agency_data": self._process_agency_data(chatbot_data.get("agency", {})),
                "landing_page_data": chatbot_data.get("landing_page", {}),
                "context": self._process_context(chatbot_data.get("context", "")),
                "welcome_message": str(chatbot_data.get("welcome_message", "¡Hola! ¿En qué puedo ayudarte?")),
                "personality": self._process_json_field(chatbot_data.get("personality"), "personality"),
                "configuration": self._process_json_field(chatbot_data.get("configuration"), "configuration"),
                "use_emojis": bool(chatbot_data.get("use_emojis", True)),
                "quick_questions": self._process_quick_questions(chatbot_data.get("quick_questions", [])),
                "context_structure": chatbot_data.get("context_structure", {}),
                "hotels": self._process_hotels_data(chatbot_data.get("hotels", []))
            }
            
            logger.info(f"Chatbot data processed successfully for {self.chatbot_id}")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error loading chatbot data: {str(e)}")
            return self._get_default_chatbot_data()

    def _process_agency_data(self, agency_data: Dict) -> Dict:
        """Procesa y estructura los datos de la agencia"""
        if not agency_data:
            return {}
            
        return {
            "id": str(agency_data.get("id", "")),
            "name": str(agency_data.get("name", "")),
            "description": str(agency_data.get("description", "")),
            "contact_info": agency_data.get("contact_info", {})
        }

    def _process_context(self, context: str) -> str:
        """Procesa y limpia el contexto del chatbot"""
        if not context:
            return ""
            
        # Eliminar espacios en blanco extras y caracteres especiales
        context = " ".join(context.split())
        return context

    def _process_json_field(self, field_value: Any, field_name: str) -> Dict:
        """Procesa campos JSON de manera segura"""
        if isinstance(field_value, dict):
            return field_value
        try:
            if isinstance(field_value, str):
                return json.loads(field_value)
            return {}
        except Exception as e:
            logger.error(f"Error parsing {field_name}: {str(e)}")
            return {}

    def _process_quick_questions(self, questions: List) -> List[str]:
        """Procesa y valida las preguntas rápidas"""
        if not isinstance(questions, list):
            return []
            
        # Filtrar y limpiar preguntas
        valid_questions = []
        for q in questions:
            if isinstance(q, str) and q.strip():
                valid_questions.append(q.strip())
                
        return valid_questions[:5]  # Limitar a 5 preguntas rápidas

    def _get_model_config(self) -> Dict[str, Any]:
        """Obtiene la configuración optimizada del modelo"""
        config = self.chatbot_data.get('configuration', {})
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except:
                config = {}
                
        return {
            "model": config.get('model', 'gpt-4-turbo-preview'),
            "temperature": float(config.get('temperature', 0.7)),
            "max_tokens": int(config.get('max_tokens', 1000)),
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }

    def _extract_suggested_actions(self, response: str) -> List[str]:
        """Extrae acciones sugeridas de la respuesta"""
        quick_questions = self.chatbot_data.get('quick_questions', [])
        if not quick_questions:
            return []
            
        # Devolver máximo 3 preguntas rápidas relevantes
        return quick_questions[:3]

    def _update_conversation_state(self, lead_id: str, user_message: str, bot_response: str):
        """Actualiza el estado de la conversación de manera eficiente"""
        if lead_id not in self._conversation_states:
            self._conversation_states[lead_id] = {'history': []}
            
        state = self._conversation_states[lead_id]
        history = state['history']
        
        # Mantener solo los últimos 10 mensajes
        if len(history) >= 10:
            history = history[-9:]
            
        history.extend([
            {'type': 'user', 'content': user_message, 'timestamp': time.time()},
            {'type': 'bot', 'content': bot_response, 'timestamp': time.time()}
        ])
        
        state['history'] = history
        self._conversation_states[lead_id] = state

    def _get_conversation_state(self, lead_id: str) -> Dict:
        """Obtiene el estado de la conversación"""
        state_key = f"{self.chatbot_id}:{lead_id}"
        if state_key not in self._conversation_states:
            self._conversation_states[state_key] = {
                'history': [],
                'last_interaction': time.time()
            }
        return self._conversation_states[state_key]

    def _build_context(self) -> str:
        """Construye el contexto para el chatbot utilizando la información disponible"""
        try:
            # Obtener datos relacionados
            related_data = self._load_related_data()
            
            # Construir contexto base con la información del chatbot
            context_parts = [
                self.chatbot_data.get('context', ''),
                "\nInformación de la Agencia:",
                f"Nombre: {self.chatbot_data.get('agency_data', {}).get('name', '')}",
                f"Descripción: {self.chatbot_data.get('agency_data', {}).get('description', '')}"
            ]
            
            # Añadir información de hoteles si está disponible
            if hotels := related_data.get('hotels', []):
                context_parts.append("\nHabitaciones y Cabañas Disponibles:")
                for hotel in hotels:
                    context_parts.append(f"\n{hotel['name']}:")
                    context_parts.append(f"- Descripción: {hotel['description']}")
                    context_parts.append(f"- Precio base: ${hotel.get('base_price', 'Consultar')}")
                    if amenities := hotel.get('amenities', []):
                        context_parts.append("- Amenidades: " + ", ".join(amenities))
                    
                    # Añadir información de tipos de habitación
                    if room_types := hotel.get('room_types', []):
                        for rt in room_types:
                            context_parts.append(f"  * {rt['name']}:")
                            context_parts.append(f"    - Capacidad: {rt.get('max_occupancy', 'No especificada')} personas")
                            context_parts.append(f"    - Precio: ${rt.get('base_price', 'Consultar')}")
            
            # Añadir información de paquetes si está disponible
            if packages := related_data.get('packages', []):
                context_parts.append("\nPaquetes Turísticos:")
                for package in packages:
                    context_parts.append(f"\n{package['name']}:")
                    context_parts.append(f"- Descripción: {package['description']}")
                    context_parts.append(f"- Duración: {package.get('duration', 'No especificada')}")
                    context_parts.append(f"- Precio: ${package.get('price', 'Consultar')}")
                    if included := package.get('included_services', {}):
                        context_parts.append("- Servicios incluidos: " + ", ".join(included))
            
            # Añadir información de parques temáticos si está disponible
            if parks := related_data.get('theme_parks', []):
                context_parts.append("\nParques Temáticos:")
                for park in parks:
                    context_parts.append(f"\n{park['name']}:")
                    context_parts.append(f"- Descripción: {park['description']}")
                    context_parts.append(f"- Ubicación: {park.get('location', 'No especificada')}")
                    if hours := park.get('operating_hours', {}):
                        context_parts.append("- Horario: " + str(hours))
                    
                    # Añadir tipos de tickets
                    if tickets := park.get('ticket_types', []):
                        context_parts.append("- Tipos de entrada:")
                        for ticket in tickets:
                            context_parts.append(f"  * {ticket['name']}: ${ticket.get('price', 'Consultar')}")
                            context_parts.append(f"    {ticket.get('description', '')}")
            
            # Unir todo el contexto
            full_context = "\n".join(context_parts)
            
            # Añadir estructura de contexto si está disponible
            if context_structure := self.chatbot_data.get('context_structure', {}):
                full_context += f"\n\nObjetivo del chatbot: {context_structure.get('purpose', '')}"
                if tone := context_structure.get('tone'):
                    full_context += f"\nTono de comunicación: {tone}"
            
            return full_context
            
        except Exception as e:
            print(f"Error building context: {str(e)}")
            return self.chatbot_data.get('context', '')

    def _load_related_data(self) -> Dict:
        """Carga datos relacionados del chatbot de manera eficiente"""
        cache_key = f"related_{self.chatbot_id}"
        
        # Verificar caché
        cached_data = self._related_data_cache.get(cache_key)
        if cached_data and time.time() - cached_data['timestamp'] < 300:
            return cached_data['data']
            
        try:
            agency_id = self.chatbot_data.get('agency_id')
            if not agency_id:
                return {}

            # Cargar todos los datos relacionados en paralelo
            hotels_response = supabase.table("hotels")\
                .select("*, room_types(*)").eq("agency_id", agency_id).execute()
                
            packages_response = supabase.table("packages")\
                .select("*, destinations(*)").eq("agency_id", agency_id).execute()
                
            theme_parks_response = supabase.table("theme_parks")\
                .select("*, ticket_types(*)").eq("agency_id", agency_id).execute()
            
            # Procesar y estructurar los datos
            related_data = {
                'hotels': self._process_hotels_data(hotels_response.data if hotels_response else []),
                'packages': self._process_packages_data(packages_response.data if packages_response else []),
                'theme_parks': self._process_theme_parks_data(theme_parks_response.data if theme_parks_response else [])
            }
            
            # Guardar en caché
            self._related_data_cache[cache_key] = {
                'data': related_data,
                'timestamp': time.time()
            }
            
            return related_data
            
        except Exception as e:
            print(f"Error loading related data: {str(e)}")
            return {}

    def _process_hotels_data(self, hotels: List[Dict]) -> List[Dict]:
        """Procesa y estructura los datos de hoteles"""
        processed_hotels = []
        for hotel in hotels:
            room_types = hotel.get('room_types', [])
            processed_hotels.append({
                'id': hotel.get('id'),
                'name': hotel.get('name'),
                'description': hotel.get('description'),
                'address': hotel.get('address'),
                'city': hotel.get('city'),
                'rating': hotel.get('rating'),
                'amenities': hotel.get('amenities', []),
                'room_types': [{
                    'id': rt.get('id'),
                    'name': rt.get('name'),
                    'description': rt.get('description'),
                    'max_occupancy': rt.get('max_occupancy'),
                    'base_price': rt.get('base_price'),
                    'amenities': rt.get('amenities', [])
                } for rt in room_types]
            })
        return processed_hotels

    def _process_packages_data(self, packages: List[Dict]) -> List[Dict]:
        """Procesa y estructura los datos de paquetes"""
        processed_packages = []
        for package in packages:
            destinations = package.get('destinations', [])
            processed_packages.append({
                'id': package.get('id'),
                'name': package.get('name'),
                'description': package.get('description'),
                'price': package.get('price'),
                'duration': package.get('duration'),
                'included_services': package.get('included_services', {}),
                'destinations': [{
                    'id': dest.get('id'),
                    'name': dest.get('name'),
                    'description': dest.get('description'),
                    'country': dest.get('country'),
                    'city': dest.get('city'),
                    'attractions': dest.get('attractions', [])
                } for dest in destinations]
            })
        return processed_packages

    def _process_theme_parks_data(self, theme_parks: List[Dict]) -> List[Dict]:
        """Procesa y estructura los datos de parques temáticos"""
        processed_parks = []
        for park in theme_parks:
            ticket_types = park.get('ticket_types', [])
            processed_parks.append({
                'id': park.get('id'),
                'name': park.get('name'),
                'description': park.get('description'),
                'location': park.get('location'),
                'operating_hours': park.get('operating_hours', {}),
                'ticket_types': [{
                    'id': tt.get('id'),
                    'name': tt.get('name'),
                    'description': tt.get('description'),
                    'price': tt.get('price'),
                    'validity_period': tt.get('validity_period')
                } for tt in ticket_types]
            })
        return processed_parks

    async def get_room_types(self, hotel_id: str) -> Dict:
        """Obtiene los tipos de habitaciones de un hotel con sus detalles"""
        try:
            response = supabase.table('room_types')\
                .select('*')\
                .eq('hotel_id', hotel_id)\
                .execute()
            return response.data
        except Exception as e:
            print(f"Error getting room types: {str(e)}")
            raise e

    async def get_room_details(self, room_type_id: str) -> Dict:
        """Obtiene los detalles completos de un tipo de habitación"""
        try:
            response = supabase.table('room_types')\
                .select('*')\
                .eq('id', room_type_id)\
                .single()\
                .execute()
            return response.data
        except Exception as e:
            print(f"Error getting room details: {str(e)}")
            raise e

    async def check_availability(self, hotel_id: str, check_in: str, check_out: str, room_type_id: Optional[str] = None) -> Dict:
        """Verifica la disponibilidad de habitaciones para las fechas especificadas"""
        try:
            # Convertir fechas a timestamp con zona horaria
            check_in_ts = f"{check_in}T00:00:00+00:00"
            check_out_ts = f"{check_out}T00:00:00+00:00"
            
            # Si no se especifica room_type_id, obtener disponibilidad de todos los tipos de habitación
            if not room_type_id:
                response = supabase.rpc(
                    'get_hotel_rooms_complete_info',
                    {
                        'p_hotel_id': hotel_id,
                        'p_check_in': check_in_ts,
                        'p_check_out': check_out_ts
                    }
                ).execute()
                return {
                    'hotel_id': hotel_id,
                    'check_in': check_in,
                    'check_out': check_out,
                    'room_types': response.data
                }
            else:
                # Obtener disponibilidad para un tipo específico de habitación
                response = supabase.rpc(
                    'get_room_availability',
                    {
                        'p_room_type_id': room_type_id,
                        'p_check_in': check_in_ts,
                        'p_check_out': check_out_ts
                    }
                ).execute()
                return {
                    'hotel_id': hotel_id,
                    'room_type_id': room_type_id,
                    'check_in': check_in,
                    'check_out': check_out,
                    'availability': response.data[0]
                }
        except Exception as e:
            print(f"Error checking availability: {str(e)}")
            raise e

    async def create_booking(self, booking_data: Dict) -> Dict:
        """Crea una nueva reserva"""
        try:
            response = supabase.rpc(
                'create_booking',
                {
                    'p_user_id': booking_data['user_id'],
                    'p_hotel_id': booking_data['hotel_id'],
                    'p_room_type_id': booking_data['room_type_id'],
                    'p_check_in': f"{booking_data['check_in']}T00:00:00+00:00",
                    'p_check_out': f"{booking_data['check_out']}T00:00:00+00:00",
                    'p_guests_count': booking_data['guests_count'],
                    'p_special_requests': booking_data.get('special_requests')
                }
            ).execute()
            
            # Obtener detalles de la reserva creada
            booking_details = await self.get_booking(response.data[0])
            return booking_details
        except Exception as e:
            print(f"Error creating booking: {str(e)}")
            raise e

    async def get_booking(self, booking_id: str) -> Dict:
        """Obtiene los detalles de una reserva"""
        try:
            response = supabase.rpc(
                'get_booking_details',
                {'p_booking_id': booking_id}
            ).execute()
            
            if not response.data:
                raise ValueError(f"Booking with ID {booking_id} not found")
                
            return response.data[0]
        except Exception as e:
            print(f"Error getting booking details: {str(e)}")
            raise e

    async def cancel_booking(self, booking_id: str, user_id: str) -> bool:
        """Cancela una reserva existente"""
        try:
            response = supabase.rpc(
                'cancel_booking',
                {
                    'p_booking_id': booking_id,
                    'p_user_id': user_id
                }
            ).execute()
            
            return response.data[0]
        except Exception as e:
            print(f"Error canceling booking: {str(e)}")
            raise e

    async def get_user_bookings(self, user_id: str) -> List[Dict]:
        """Obtiene todas las reservas de un usuario"""
        try:
            response = supabase.rpc(
                'get_user_bookings',
                {'p_user_id': user_id}
            ).execute()
            
            return response.data
        except Exception as e:
            print(f"Error getting user bookings: {str(e)}")
            raise e

    def _get_default_chatbot_data(self) -> Dict:
        """Retorna datos por defecto para el chatbot"""
        return {
            "id": self.chatbot_id,
            "name": "Assistant",
            "description": "Virtual Assistant",
            "agency_id": "",
            "agency_data": {},
            "landing_page_data": {},
            "context": "",
            "welcome_message": "¡Hola! ¿En qué puedo ayudarte?",
            "personality": self._ensure_personality_defaults({}),
            "configuration": self._ensure_configuration_defaults({}),
            "use_emojis": True,
            "quick_questions": [],
            "context_structure": {}
        }

    def _ensure_personality_defaults(self, personality: Dict) -> Dict:
        """Asegura valores por defecto para la personalidad"""
        defaults = {
            "tone": "profesional",
            "formality_level": "semiformal",
            "emoji_usage": "moderado",
            "language_style": "claro y conciso"
        }
        
        if not isinstance(personality, dict):
            return defaults
            
        return {**defaults, **personality}

    def _ensure_configuration_defaults(self, configuration: Dict) -> Dict:
        """Asegura valores por defecto para la configuración"""
        defaults = {
            "temperature": 0.7,
            "model": "gpt-4-turbo-preview",
            "max_tokens": 1000
        }
        
        if not isinstance(configuration, dict):
            return defaults
            
        return {**defaults, **configuration}