# app/core/chatbot.py
from typing import Dict, List, Optional
import json
import os
from app.core.openai_client import client
from app.core.supabase import supabase, get_supabase_client

class ChatbotManager:
    # Diccionario para mantener el estado de las conversaciones
    _conversation_states = {}
    
    def __init__(self, chatbot_id: str):
        self.chatbot_id = chatbot_id
        self.chatbot_data = self._load_chatbot_data()
        self.context = self._build_context()
        self.conversation_history = []

    def _get_conversation_state(self, lead_id: str) -> dict:
        """Obtiene el estado de una conversación específica"""
        if not lead_id:
            return {"started": False, "history": []}
            
        key = f"{self.chatbot_id}:{lead_id}"
        if key not in self._conversation_states:
            self._conversation_states[key] = {
                "started": False,
                "history": []
            }
        return self._conversation_states[key]

    def _update_conversation_state(self, lead_id: str, state: dict):
        """Actualiza el estado de una conversación específica"""
        if lead_id:
            key = f"{self.chatbot_id}:{lead_id}"
            self._conversation_states[key] = state

    async def process_message(self, message: str, lead_id: str = None, audio_content: str = None) -> Dict:
        """Procesa un mensaje y retorna la respuesta"""
        try:
            print(f"Processing message for lead_id: {lead_id}")
            
            # Obtener el estado actual de la conversación
            conv_state = self._get_conversation_state(lead_id)
            print(f"Conversation state: {conv_state}")
            
            # Si es el primer mensaje de esta conversación
            if not conv_state["started"]:
                print("First message of conversation, sending welcome message")
                conv_state["started"] = True
                welcome_message = self.chatbot_data["welcome_message"]
                conv_state["history"].append({"role": "assistant", "content": welcome_message})
                
                # Actualizar el estado
                self._update_conversation_state(lead_id, conv_state)
                
                return {
                    "response": welcome_message,
                    "suggested_actions": [],
                    "context": {
                        "is_welcome": True,
                        "chatbot_name": self.chatbot_data["name"]
                    }
                }
            
            print(f"Processing regular message: {message}")
            
            # Añadir el mensaje del usuario al historial
            conv_state["history"].append({"role": "user", "content": message})
            
            # Construir mensajes para la API
            messages = [{"role": "system", "content": self.context}]
            
            # Añadir historial reciente
            recent_history = conv_state["history"][-10:] if len(conv_state["history"]) > 10 else conv_state["history"]
            messages.extend(recent_history)
            
            print(f"Sending {len(messages)} messages to OpenAI")
            
            # Obtener la respuesta de OpenAI
            response = await client.chat.completions.create(
                model=self.chatbot_data["configuration"]["model"],
                messages=messages,
                temperature=self.chatbot_data["configuration"]["temperature"],
                max_tokens=self.chatbot_data["configuration"]["max_tokens"],
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            # Procesar la respuesta
            assistant_message = response.choices[0].message.content
            conv_state["history"].append({"role": "assistant", "content": assistant_message})
            
            # Actualizar el estado
            self._update_conversation_state(lead_id, conv_state)
            
            print(f"Generated response: {assistant_message[:100]}...")
            
            return {
                "response": assistant_message,
                "suggested_actions": [],
                "context": {
                    "conversation_length": len(conv_state["history"]),
                    "chatbot_name": self.chatbot_data["name"],
                    "personality": self.chatbot_data["personality"],
                    "is_welcome": False
                }
            }
            
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            return {
                "response": "Lo siento, ha ocurrido un error al procesar tu mensaje. Por favor, intenta nuevamente.",
                "suggested_actions": [],
                "context": {
                    "error": str(e)
                }
            }

    def _load_chatbot_data(self) -> Dict:
        """Carga la información del chatbot desde Supabase"""
        try:
            if not supabase:
                raise ValueError("Supabase client is not initialized")
            
            response = supabase.table("chatbots").select("*").eq("id", self.chatbot_id).execute()
            if not response.data:
                raise ValueError(f"No chatbot found with id {self.chatbot_id}")
            
            chatbot_data = response.data[0]
            
            # Asegurar que tenemos los campos mínimos necesarios
            return {
                "id": chatbot_data.get("id", self.chatbot_id),
                "name": chatbot_data.get("name", "Assistant"),
                "description": chatbot_data.get("description", ""),
                "purpose": chatbot_data.get("purpose", "Asistente virtual"),
                "welcome_message": chatbot_data.get("welcome_message", "¡Hola! ¿En qué puedo ayudarte?"),
                "personality": chatbot_data.get("personality", {
                    "tone": "profesional",
                    "formality_level": "semiformal",
                    "emoji_usage": "moderado",
                    "language_style": "claro y conciso"
                }),
                "key_points": chatbot_data.get("key_points", []),
                "special_instructions": chatbot_data.get("special_instructions", []),
                "example_qa": chatbot_data.get("example_qa", []),
                "configuration": chatbot_data.get("configuration", {
                    "temperature": 0.7,
                    "model": "gpt-4-turbo-preview",
                    "max_tokens": 1000
                })
            }
            
        except Exception as e:
            print(f"Error loading chatbot data: {str(e)}")
            if os.getenv("ENVIRONMENT") != "production":
                print("Using mock data in development")
                return {
                    "id": self.chatbot_id,
                    "name": "Development Assistant",
                    "description": "Development chatbot",
                    "purpose": "Testing and development",
                    "welcome_message": "¡Hola! Soy un chatbot de prueba.",
                    "personality": {
                        "tone": "profesional",
                        "formality_level": "semiformal",
                        "emoji_usage": "moderado",
                        "language_style": "claro y conciso"
                    },
                    "key_points": ["Test point"],
                    "special_instructions": ["Test instruction"],
                    "example_qa": [{"question": "Test?", "answer": "Test answer"}],
                    "configuration": {
                        "temperature": 0.7,
                        "model": "gpt-4-turbo-preview",
                        "max_tokens": 1000
                    }
                }
            raise

    def _build_context(self) -> str:
        """Construye el contexto inicial del chatbot"""
        try:
            personality = self.chatbot_data["personality"]
            key_points = self.chatbot_data["key_points"]
            special_instructions = self.chatbot_data["special_instructions"]
            example_qa = self.chatbot_data["example_qa"]
            
            context_parts = [
                f"Eres un asistente virtual para una agencia de viajes llamado {self.chatbot_data['name']}.",
                f"Propósito: {self.chatbot_data['purpose']}",
                "",
                "PERSONALIDAD Y ESTILO DE COMUNICACIÓN:",
                f"- Tono: {personality['tone']}",
                f"- Nivel de formalidad: {personality['formality_level']}",
                f"- Uso de emojis: {personality['emoji_usage']}",
                f"- Estilo de lenguaje: {personality['language_style']}",
                ""
            ]
            
            if key_points:
                context_parts.extend([
                    "PUNTOS CLAVE A CONSIDERAR:",
                    *[f"- {point}" for point in key_points],
                    ""
                ])
            
            if special_instructions:
                context_parts.extend([
                    "INSTRUCCIONES ESPECIALES:",
                    *[f"- {instruction}" for instruction in special_instructions],
                    ""
                ])
            
            if example_qa:
                context_parts.extend([
                    "EJEMPLOS DE PREGUNTAS Y RESPUESTAS:",
                    *[f"P: {qa['question']}\nR: {qa['answer']}" for qa in example_qa],
                    ""
                ])
            
            context_parts.append(
                f"Recuerda mantener un tono {personality['tone']} y un nivel de formalidad {personality['formality_level']} en todas tus respuestas."
            )
            
            return "\n".join(context_parts)
            
        except Exception as e:
            print(f"Error building context: {str(e)}")
            return "Eres un asistente virtual para una agencia de viajes. Ayuda a los usuarios con sus consultas de manera profesional y clara."

    async def get_room_types(self, hotel_id: str) -> List[Dict]:
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