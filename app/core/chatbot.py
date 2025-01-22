# app/core/chatbot.py
from typing import Dict, List, Optional
import json
import os
from app.core.openai_client import client
from app.core.supabase import supabase, get_supabase_client

class ChatbotManager:
    def __init__(self, chatbot_id: str):
        self.chatbot_id = chatbot_id
        self.chatbot_data = self._load_chatbot_data()
        self.context = self._build_context()

    def _load_chatbot_data(self) -> Dict:
        """Carga la información del chatbot desde Supabase"""
        if not supabase:
            print("Error: Supabase client is None")
            # En desarrollo, usar datos mock si Supabase no está disponible
            if os.getenv("ENVIRONMENT") != "production":
                print("Using mock data in development")
                return {
                    "id": self.chatbot_id,
                    "name": "Development Chatbot",
                    "description": "Chatbot for development",
                    "initial_prompt": "You are a helpful travel assistant.",
                    "context": "Default context for development",
                    "agency_id": "agency_id",
                    "system_prompt": "You are a travel assistant. Help users plan their trips and provide information about tourist destinations.",
                    "max_turns": 10,
                    "configuration": {
                        "temperature": 0.7
                    }
                }
            raise ValueError("Supabase client is not initialized")

        try:
            print(f"Attempting to fetch chatbot with ID: {self.chatbot_id}")
            response = supabase.table('chatbots').select('*').eq('id', self.chatbot_id).execute()
            print(f"Supabase response type: {type(response)}")
            
            # Handle different response types
            if isinstance(response, dict):
                data = response.get('data', [])
            else:
                data = getattr(response, 'data', [])
            
            print(f"Data from response: {data}")
            
            if not data:
                print(f"No chatbot found with ID {self.chatbot_id}")
                if os.getenv("ENVIRONMENT") != "production":
                    return {
                        "id": self.chatbot_id,
                        "name": "Development Chatbot",
                        "description": "Chatbot for development",
                        "initial_prompt": "You are a helpful travel assistant.",
                        "context": "Default context for development",
                        "agency_id": "agency_id",
                        "system_prompt": "You are a travel assistant. Help users plan their trips and provide information about tourist destinations.",
                        "max_turns": 10,
                        "configuration": {
                            "temperature": 0.7
                        }
                    }
                raise ValueError(f"Chatbot with ID {self.chatbot_id} not found")
                
            return data[0]
        except Exception as e:
            print(f"Error in _load_chatbot_data: {str(e)}")
            if os.getenv("ENVIRONMENT") == "production":
                raise Exception(f"Error loading chatbot data: {str(e)}")
            # En desarrollo, usar datos mock
            print("Using mock data due to error")
            return {
                "id": self.chatbot_id,
                "name": "Development Chatbot",
                "description": "Chatbot for development",
                "initial_prompt": "You are a helpful travel assistant.",
                "context": "Default context for development",
                "agency_id": "agency_id",
                "system_prompt": "You are a travel assistant. Help users plan their trips and provide information about tourist destinations.",
                "max_turns": 10,
                "configuration": {
                    "temperature": 0.7
                }
            }

    def _build_context(self) -> str:
        """Construye el contexto inicial del chatbot"""
        try:
            agency_id = self.chatbot_data['agency_id']
            
            # Obtener información de la agencia
            agency = supabase.table('agencies').select('*').eq('id', agency_id).execute().data[0]
            
            # Obtener hoteles
            hotels = supabase.table('hotels').select('*').eq('agency_id', agency_id).execute().data
            
            # Obtener paquetes
            packages = supabase.table('packages').select('*').eq('agency_id', agency_id).execute().data
            
            # Construir contexto base
            context = f"""
            You are a travel assistant for {agency['name']}.
            Context: {self.chatbot_data.get('context', '')}
            
            Available Hotels:
            {json.dumps(hotels, indent=2)}
            
            Available Packages:
            {json.dumps(packages, indent=2)}
            
            Instructions:
            - Always be helpful and professional
            - You can check room availability and make bookings
            - You can provide information about hotels and packages
            - If you need to create a booking, use the booking API
            """
            return context
        except Exception as e:
            if os.getenv("ENVIRONMENT") == "production":
                raise Exception(f"Error building context: {str(e)}")
            return "You are a helpful travel assistant. This is a development context."

    async def process_message(self, message: str, lead_id: str = None) -> str:
        """Procesa un mensaje y retorna la respuesta"""
        
        # Obtener historial de mensajes recientes si existe lead_id
        messages = []
        if lead_id:
            recent_messages = supabase.table('chat_messages')\
                .select('*')\
                .eq('lead_id', lead_id)\
                .order('created_at', desc=True)\
                .limit(5)\
                .execute().data
                
            for msg in reversed(recent_messages):
                role = "assistant" if msg['is_bot'] else "user"
                messages.append({"role": role, "content": msg['message']})

        # Agregar contexto y mensaje actual
        messages = [
            {"role": "system", "content": self.context},
            *messages,
            {"role": "user", "content": message}
        ]

        # Obtener respuesta de ChatGPT
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=self.chatbot_data.get('configuration', {}).get('temperature', 0.7),
                max_tokens=500,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            assistant_message = response.choices[0].message.content
        except Exception as e:
            print(f"Error calling OpenAI API: {str(e)}")
            raise e

        # Guardar mensaje en la base de datos si existe lead_id
        if lead_id:
            supabase.table('chat_messages').insert([{
                'chatbot_id': self.chatbot_id,
                'lead_id': lead_id,
                'message': message,
                'is_bot': False,
                'metadata': {}
            }]).execute()

            supabase.table('chat_messages').insert([{
                'chatbot_id': self.chatbot_id,
                'lead_id': lead_id,
                'message': assistant_message,
                'is_bot': True,
                'metadata': {}
            }]).execute()

        return assistant_message

    async def check_availability(self, hotel_id: str, check_in: str, check_out: str) -> Dict:
        """Verifica la disponibilidad de habitaciones"""
        query = supabase.rpc(
            'check_room_availability',
            {'p_room_type_id': hotel_id, 'p_check_in': check_in, 'p_check_out': check_out}
        ).execute()
        return query.data

    async def create_booking(self, booking_data: Dict) -> Dict:
        """Crea una nueva reserva"""
        response = supabase.rpc(
            'create_booking',
            booking_data
        ).execute()
        return response.data