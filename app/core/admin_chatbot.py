import traceback
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain.schema import (
    SystemMessage,
    HumanMessage,
    AIMessage
)
from app.core.supabase import get_supabase_client
from app.models.admin_schemas import AdminChatResponse
import json
from app.models.ui_components import UIComponent, UIComponentType

class AdminChatbotManager:
    def __init__(self, agency_id: str, user_id: str):
        print("Inicializando AdminChatbotManager...")
        self.agency_id = agency_id
        self.user_id = user_id
        self.supabase = get_supabase_client()
        self.user_data = self._load_user_data()
        print(f"Datos de usuario cargados: {self.user_data}")
        self.agency_data = self._load_agency_data()
        print(f"Datos de agencia cargados: {self.agency_data}")
        self.llm = self._initialize_llm()
        self.conversation_history = []
        self.current_form = None
        self.current_form_data = {}
        self._initialize_conversation()
        print("AdminChatbotManager inicializado correctamente")

    def _load_user_data(self) -> Dict:
        """Carga la información del usuario administrador"""
        response = self.supabase.table("profiles").select("*").eq("id", self.user_id).execute()
        return response.data[0] if response.data else {}

    def _load_agency_data(self) -> Dict:
        """Carga la información de la agencia y sus activos"""
        response = self.supabase.table("agencies").select("*").eq("id", self.agency_id).execute()
        return response.data[0] if response.data else {}

    def _initialize_llm(self) -> ChatOpenAI:
        """Inicializa el modelo de lenguaje"""
        print("Inicializando modelo LLM...")
        try:
            model = ChatOpenAI(
                temperature=0.7,
                model_name="gpt-4-turbo-preview",
                streaming=False,
                request_timeout=120,
                max_retries=3
            )
            print("Modelo LLM inicializado correctamente")
            return model
        except Exception as e:
            print(f"Error al inicializar LLM: {str(e)}")
            raise

    def _initialize_conversation(self) -> None:
        """Inicializa la conversación con un mensaje de bienvenida"""
        print("Inicializando conversación...")
        system_prompt = self._get_system_prompt()
        print(f"System prompt generado: {system_prompt[:100]}...")
        
        self.conversation_history = [
            SystemMessage(content=system_prompt),
            AIMessage(content="""¡Hola! Soy tu asistente administrativo. Puedo ayudarte con las siguientes tareas:

1. Gestión de Hoteles:
   - Crear hotel
   - Editar hotel
   - Eliminar hotel
   - Listar hoteles
   - Ver detalles de hotel

2. Gestión de Habitaciones:
   - Crear tipo de habitación
   - Editar tipo de habitación
   - Eliminar tipo de habitación
   - Listar tipos de habitación

3. Gestión de Reservas:
   - Ver reservas
   - Actualizar estado de reserva
   - Cancelar reserva

4. Gestión de Leads:
   - Ver leads
   - Actualizar estado de lead
   - Ver historial de conversación

¿En qué puedo ayudarte?""")
        ]
        print("Conversación inicializada correctamente")

    def _get_system_prompt(self) -> str:
        """Obtiene el prompt del sistema con el contexto actual"""
        return f"""Eres un asistente administrativo experto para la agencia de viajes {self.agency_data.get('name', 'Agencia')}.
        
        Información del usuario:
        Nombre: Administrador
        Rol: {self.user_data.get('role', 'admin')}
        
        Contexto de la agencia:
        {json.dumps(self.agency_data, indent=2)}
        
        Tu objetivo es ayudar al administrador a gestionar la agencia de viajes. Debes guiar al usuario a través de los procesos de creación, edición y eliminación de recursos paso a paso.
        
        Cuando el usuario quiera crear o editar algo:
        1. Pide los datos necesarios uno por uno
        2. Valida cada dato antes de continuar
        3. Al final, muestra un resumen y pide confirmación
        
        Mantén un tono profesional y específico. Guía al usuario paso a paso."""

    async def process_message(self, message: str) -> AdminChatResponse:
        """Procesa un mensaje del usuario y retorna una respuesta"""
        try:
            print(f"\nProcesando mensaje: {message}")
            
            # Si hay un formulario activo, procesar la entrada del formulario
            if self.current_form:
                return await self._process_form_input(message)
            
            # Si no hay formulario activo, analizar la intención
            response = await self._analyze_intent(message)
            return response
            
        except Exception as e:
            print(f"Error en process_message: {str(e)}")
            print(f"Traceback completo: {traceback.format_exc()}")
            return AdminChatResponse(
                message="Lo siento, ocurrió un error al procesar tu mensaje. Por favor, intenta de nuevo."
            )

    async def _analyze_intent(self, message: str) -> AdminChatResponse:
        """Analiza la intención del mensaje del usuario"""
        try:
            print(f"\nAnalizando intención: {message}")
            message_lower = message.lower()
            
            # Lista de intenciones conocidas
            if "crear chatbot" in message_lower:
                self.current_form = "create_chatbot"
                self.current_form_data = {}
                return AdminChatResponse(
                    message="Ingresa el nombre del chatbot (requerido):",
                    components=[
                        UIComponent(
                            type=UIComponentType.TEXT_INPUT,
                            id="chatbot_name",
                            label="Nombre del Chatbot",
                            placeholder="Ej: AsistenteBot",
                            required=True
                        ).dict()
                    ]
                )
            
            # Si no es una intención conocida, usar el LLM
            print("Usando LLM para procesar mensaje...")
            self.conversation_history.append(HumanMessage(content=message))
            response = await self.llm.agenerate([self.conversation_history])
            ai_message = response.generations[0][0].text
            self.conversation_history.append(AIMessage(content=ai_message))
            
            return AdminChatResponse(message=ai_message)
            
        except Exception as e:
            print(f"Error en _analyze_intent: {str(e)}")
            return AdminChatResponse(
                message="Lo siento, ocurrió un error al analizar tu mensaje. Por favor, intenta de nuevo."
            )

    async def _process_form_input(self, message: str) -> AdminChatResponse:
        """Procesa la entrada del usuario durante un formulario"""
        try:
            if self.current_form == "create_chatbot":
                return await self._process_chatbot_form(message)
            elif self.current_form == "create_hotel":
                return await self._process_hotel_form(message)
            elif self.current_form == "create_room_type":
                return await self._process_room_type_form(message)
            else:
                self.current_form = None
                return AdminChatResponse(
                    message="Lo siento, no reconozco este tipo de formulario."
                )
        except Exception as e:
            print(f"Error en _process_form_input: {str(e)}")
            return AdminChatResponse(
                message="Lo siento, ocurrió un error al procesar tu entrada. Por favor, intenta de nuevo."
            )

    async def _process_chatbot_form(self, message: str) -> AdminChatResponse:
        """Procesa el formulario de creación de chatbot"""
        try:
            if "nombre" not in self.current_form_data:
                self.current_form_data["nombre"] = message
                return AdminChatResponse(
                    message="Ingresa una descripción breve del chatbot (requerido):",
                    components=[
                        UIComponent(
                            type=UIComponentType.TEXT_INPUT,
                            id="chatbot_description",
                            label="Descripción",
                            placeholder="Ej: Asistente para reservas y consultas",
                            required=True
                        ).dict()
                    ]
                )
            
            elif "descripcion" not in self.current_form_data:
                self.current_form_data["descripcion"] = message
                return AdminChatResponse(
                    message="¿Deseas agregar un ícono para el chatbot? (opcional)",
                    components=[
                        UIComponent(
                            type=UIComponentType.FILE_INPUT,
                            id="chatbot_icon",
                            label="Ícono",
                            placeholder="Seleccionar imagen...",
                            required=False,
                            validation={
                                "accept": "image/*",
                                "maxSize": 2097152
                            }
                        ).dict()
                    ]
                )
            
            elif "icon_url" not in self.current_form_data:
                self.current_form_data["icon_url"] = message if message.startswith('http') else None
                
                return AdminChatResponse(
                    message=f"Confirma los datos del chatbot:\n\nNombre: {self.current_form_data['nombre']}\nDescripción: {self.current_form_data['descripcion']}\nÍcono: {'Sí' if self.current_form_data['icon_url'] else 'No'}",
                    components=[
                        UIComponent(
                            type=UIComponentType.CONFIRMATION,
                            id="confirm_chatbot",
                            label="¿Crear chatbot?",
                            options=[
                                {"value": "si", "label": "Sí"},
                                {"value": "no", "label": "No"}
                            ]
                        ).dict()
                    ]
                )
            
            elif message.lower() in ['si', 'sí', 'yes']:
                chatbot_data = {
                    "agency_id": self.agency_id,
                    "name": self.current_form_data["nombre"],
                    "description": self.current_form_data["descripcion"],
                    "icon_url": self.current_form_data["icon_url"],
                    "configuration": {
                        "welcome_message": f"¡Hola! Soy {self.current_form_data['nombre']}, ¿en qué puedo ayudarte?"
                    }
                }
                
                response = self.supabase.table("chatbots").insert(chatbot_data).execute()
                
                self.current_form = None
                self.current_form_data = {}
                
                return AdminChatResponse(
                    message="✅ Chatbot creado exitosamente.",
                    action_required=False
                )
            
            elif message.lower() in ['no']:
                self.current_form = None
                self.current_form_data = {}
                return AdminChatResponse(
                    message="❌ Operación cancelada.",
                    action_required=False
                )
            
            return AdminChatResponse(
                message="Por favor responde 'si' o 'no'.",
                components=[
                    UIComponent(
                        type=UIComponentType.CONFIRMATION,
                        id="confirm_chatbot",
                        label="¿Crear chatbot?",
                        options=[
                            {"value": "si", "label": "Sí"},
                            {"value": "no", "label": "No"}
                        ]
                    ).dict()
                ]
            )
            
        except Exception as e:
            print(f"Error en _process_chatbot_form: {str(e)}")
            self.current_form = None
            self.current_form_data = {}
            return AdminChatResponse(
                message="❌ Lo siento, ocurrió un error al crear el chatbot. Por favor, intenta de nuevo.",
                action_required=False
            )
