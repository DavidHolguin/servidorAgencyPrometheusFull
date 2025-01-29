"""Admin chatbot manager module."""
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain.schema import (
    SystemMessage,
    HumanMessage,
    AIMessage
)
from app.core.supabase import get_supabase_client
from app.models.admin_schemas import AdminChatResponse
from app.models.ui_components import UIComponent, UIComponentType
from app.core.admin.intent import (
    IntentDetector,
    ResponseGenerator,
    ConversationState,
    IntentType,
    EntityType,
    Intent
)

class AdminChatbotManager:
    """Main class for handling administrative tasks through chatbot interface."""
    
    def __init__(self, agency_id: str, user_id: str):
        """Initialize the admin chatbot manager."""
        print("Inicializando AdminChatbotManager...")
        self.agency_id = agency_id
        self.user_id = user_id
        self.supabase = get_supabase_client()
        
        # Load user and agency data
        self.user_data = self._load_user_data()
        print(f"Datos de usuario cargados: {self.user_data}")
        self.agency_data = self._load_agency_data()
        print(f"Datos de agencia cargados: {self.agency_data}")
        
        # Initialize components
        self.llm = self._initialize_llm()
        self.intent_detector = IntentDetector()
        self.response_generator = ResponseGenerator()
        self.conversation_state = ConversationState()
        
        # Initialize conversation
        self._initialize_conversation()
        print("AdminChatbotManager inicializado correctamente")

    def _load_user_data(self) -> Dict:
        """Load user profile data."""
        response = self.supabase.table("profiles").select("*").eq("id", self.user_id).execute()
        return response.data[0] if response.data else {}

    def _load_agency_data(self) -> Dict:
        """Load agency data."""
        response = self.supabase.table("agencies").select("*").eq("id", self.agency_id).execute()
        return response.data[0] if response.data else {}

    def _initialize_llm(self) -> ChatOpenAI:
        """Initialize the language model."""
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
        """Initialize the conversation with system prompt."""
        print("Inicializando conversación...")
        system_prompt = self._get_system_prompt()
        welcome_message = self._get_welcome_message()
        
        # Add to conversation history
        self.conversation_state.add_to_history("system", system_prompt)
        self.conversation_state.add_to_history("assistant", welcome_message)

    def _get_system_prompt(self) -> str:
        """Get the system prompt with current context."""
        return f"""Eres un asistente administrativo profesional para la agencia de viajes {self.agency_data.get('name', 'Agencia')}.
        
        Información del usuario:
        Nombre: {self.user_data.get('name', 'Administrador')}
        Rol: {self.user_data.get('role', 'admin')}
        
        Tu objetivo es asistir al administrador en la gestión de chatbots y otros recursos de la agencia.
        
        Directrices:
        1. Mantén un tono formal y profesional
        2. Sé conciso y directo en las preguntas
        3. Valida cada entrada antes de continuar
        4. Mantén el contexto del proceso actual
        5. Confirma antes de realizar operaciones irreversibles
        6. Proporciona retroalimentación clara después de cada operación"""

    def _get_welcome_message(self) -> str:
        """Get the welcome message."""
        return """¡Bienvenido! Soy su asistente administrativo. ¿En qué puedo ayudarle?

Operaciones principales:
• Chatbots:
  - Crear nuevo chatbot
  - Ver lista de chatbots
  - Ver detalles de chatbot
  - Editar configuración
  - Eliminar chatbot

¿Qué desea hacer?"""

    async def _handle_help_intent(self) -> AdminChatResponse:
        """Handle help intent."""
        return AdminChatResponse(
            message=self._get_welcome_message(),
            success=True
        )

    async def _handle_create_chatbot(self, intent: Intent, message: str) -> AdminChatResponse:
        """Handle chatbot creation process."""
        try:
            # If waiting for confirmation
            if self.conversation_state.confirmation_pending:
                if message.lower() in ['si', 'sí', 'yes']:
                    # Create chatbot in database
                    chatbot_data = self.conversation_state.collected_data
                    chatbot_data['agency_id'] = self.agency_id
                    
                    response = self.supabase.table('chatbots').insert(chatbot_data).execute()
                    
                    # Clear state and return success message
                    self.conversation_state.clear_state()
                    return AdminChatResponse(
                        message="✅ ¡Chatbot creado exitosamente!",
                        success=True,
                        data=response.data[0] if response.data else {}
                    )
                elif message.lower() in ['no', 'cancelar']:
                    # Clear state and return cancellation message
                    self.conversation_state.clear_state()
                    return AdminChatResponse(
                        message="❌ Operación cancelada. ¿Hay algo más en lo que pueda ayudarle?",
                        success=True
                    )
                else:
                    return AdminChatResponse(
                        message="Por favor responda 'sí' o 'no'.",
                        success=True
                    )
            
            # If no active process, start one
            if not self.conversation_state.active_process:
                self.conversation_state.start_process(
                    "create_chatbot",
                    EntityType.CHATBOT,
                    self.response_generator.entity_fields[EntityType.CHATBOT]["required"]
                )
            
            # If in process, handle data collection
            if message.strip():
                current_field = self.conversation_state.missing_fields[0]
                self.conversation_state.add_data(current_field, message)
            
            # If all data collected, ask for confirmation
            if self.conversation_state.is_process_complete():
                self.conversation_state.confirmation_pending = True
                return AdminChatResponse(
                    message=self.response_generator.get_confirmation_message(self.conversation_state),
                    success=True
                )
            
            # Ask for next field
            return AdminChatResponse(
                message=self.response_generator.get_next_question(self.conversation_state),
                success=True
            )
            
        except Exception as e:
            self.conversation_state.clear_state()
            return AdminChatResponse(
                message=self.response_generator.get_error_message("server", str(e)),
                success=False
            )

    async def _handle_list_chatbots(self) -> AdminChatResponse:
        """Handle listing chatbots."""
        try:
            response = self.supabase.table('chatbots').select('*').eq('agency_id', self.agency_id).execute()
            chatbots = response.data
            
            if not chatbots:
                return AdminChatResponse(
                    message="No hay chatbots creados aún. ¿Desea crear uno nuevo?",
                    success=True
                )
            
            message = f"Encontré {len(chatbots)} chatbot(s):\n\n"
            for chatbot in chatbots:
                message += f"• {chatbot['name']}\n"
                if chatbot.get('description'):
                    message += f"  {chatbot['description']}\n"
            
            return AdminChatResponse(
                message=message,
                success=True,
                data={"chatbots": chatbots}
            )
            
        except Exception as e:
            return AdminChatResponse(
                message=self.response_generator.get_error_message("server", str(e)),
                success=False
            )

    async def _handle_view_chatbot(self, intent: Intent) -> AdminChatResponse:
        """Handle viewing chatbot details."""
        try:
            chatbot_id = intent.params.get('id')
            if not chatbot_id:
                return AdminChatResponse(
                    message="Por favor especifique el ID del chatbot que desea ver.",
                    success=False
                )
            
            response = self.supabase.table('chatbots').select('*').eq('id', chatbot_id).execute()
            if not response.data:
                return AdminChatResponse(
                    message=self.response_generator.get_error_message("not_found", "No se encontró el chatbot especificado."),
                    success=False
                )
            
            chatbot = response.data[0]
            message = f"Detalles del chatbot:\n\n"
            message += f"• Nombre: {chatbot['name']}\n"
            message += f"• Descripción: {chatbot['description']}\n"
            message += f"• Mensaje de bienvenida: {chatbot.get('welcome_message', 'No definido')}\n"
            message += f"• Modelo: {chatbot.get('model_config', {}).get('model', 'gpt-4')}\n"
            
            return AdminChatResponse(
                message=message,
                success=True,
                data={"chatbot": chatbot}
            )
            
        except Exception as e:
            return AdminChatResponse(
                message=self.response_generator.get_error_message("server", str(e)),
                success=False
            )

    async def process_message(self, message: str) -> AdminChatResponse:
        """Process an incoming message and return a response."""
        try:
            # Add user message to history
            self.conversation_state.add_to_history("user", message)
            
            # Convert conversation history to LangChain format
            langchain_history = []
            for msg in self.conversation_state.conversation_history:
                if msg["role"] == "system":
                    langchain_history.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    langchain_history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_history.append(AIMessage(content=msg["content"]))
            
            # Detect intent
            intent = await self.intent_detector.detect_intent(
                message,
                self.conversation_state.conversation_history
            )
            
            print(f"Intención detectada: {intent.type.value} - {intent.entity.value} ({intent.confidence})")
            
            # If in a process, continue with it
            if self.conversation_state.active_process:
                if intent.type == IntentType.HELP or message.lower() in ['cancelar', 'salir', 'terminar']:
                    self.conversation_state.clear_state()
                    return await self._handle_help_intent()
                elif self.conversation_state.active_process == "create_chatbot":
                    return await self._handle_create_chatbot(intent, message)
            
            # Handle new intents
            if intent.type == IntentType.HELP:
                return await self._handle_help_intent()
            elif intent.type == IntentType.CREATE and intent.entity == EntityType.CHATBOT:
                return await self._handle_create_chatbot(intent, "")
            elif intent.type == IntentType.LIST and intent.entity == EntityType.CHATBOT:
                return await self._handle_list_chatbots()
            elif intent.type == IntentType.VIEW and intent.entity == EntityType.CHATBOT:
                return await self._handle_view_chatbot(intent)
            
            # For unknown intents, use LLM
            response = await self.llm.agenerate([langchain_history])
            ai_message = response.generations[0][0].text
            
            # Add assistant response to history
            self.conversation_state.add_to_history("assistant", ai_message)
            
            return AdminChatResponse(
                message=ai_message,
                success=True
            )
            
        except Exception as e:
            print(f"Error en process_message: {str(e)}")
            return AdminChatResponse(
                message=self.response_generator.get_error_message("server", str(e)),
                success=False
            )
