"""Admin chatbot manager module."""
from typing import Dict, List, Optional, Any, Tuple
from langchain_openai import ChatOpenAI
from langchain.schema import (
    SystemMessage,
    HumanMessage,
    AIMessage
)
from app.core.supabase import get_supabase_client
from app.models.admin_schemas import AdminChatResponse
from .chatbots import ChatbotManager
from .hotels import HotelManager
from .leads import LeadManager
from .intent import (
    IntentDetector, 
    ResponseGenerator, 
    ConversationState,
    IntentType,
    EntityType
)

class AdminChatbotManager:
    """Main class for handling administrative tasks through chatbot interface."""
    
    def __init__(self, agency_id: str, user_id: str):
        """Initialize the admin chatbot manager."""
        self.agency_id = agency_id
        self.user_id = user_id
        self.supabase = get_supabase_client()
        
        # Load user and agency data
        self.user_data = self._load_user_data()
        self.agency_data = self._load_agency_data()
        
        # Initialize managers
        self.chatbot_manager = ChatbotManager(agency_id)
        self.hotel_manager = HotelManager(agency_id)
        self.lead_manager = LeadManager(agency_id)
        
        # Initialize conversation components
        self.llm = self._initialize_llm()
        self.intent_detector = IntentDetector()
        self.response_generator = ResponseGenerator()
        self.conversation_state = ConversationState()
        self.conversation_history = []
        self._initialize_conversation()
        
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
        return ChatOpenAI(
            temperature=0.7,
            model_name="gpt-4-turbo-preview",
            streaming=False,
            request_timeout=120,
            max_retries=3
        )
        
    def _initialize_conversation(self) -> None:
        """Initialize the conversation with system prompt."""
        system_prompt = self._get_system_prompt()
        welcome_message = self._get_welcome_message()
        
        self.conversation_history = [
            SystemMessage(content=system_prompt),
            AIMessage(content=welcome_message)
        ]
        
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the chatbot."""
        return f"""Asistente administrativo para {self.agency_data.get('name', 'la agencia')}.
Respuestas concisas y profesionales. Priorizar eficiencia."""
        
    def _get_welcome_message(self) -> str:
        """Get the welcome message listing available operations."""
        return """¡Bienvenido! ¿En qué puedo ayudarle?

Operaciones principales:
• Chatbots: crear, editar, eliminar, listar
• Hoteles: crear, editar, eliminar, listar
• Leads: ver, actualizar, estadísticas
• Reservas: ver, actualizar, estadísticas

¿Qué desea hacer?"""

    def _handle_confirmation(self, message: str) -> Tuple[bool, bool]:
        """Handle confirmation messages."""
        positive = ["si", "sí", "confirmar", "proceder", "ok", "dale"]
        negative = ["no", "cancelar", "abortar", "detener"]
        
        message = message.lower()
        is_confirmation = any(word in message for word in positive + negative)
        confirmed = any(word in message for word in positive)
        
        return is_confirmation, confirmed

    async def _handle_create_intent(self, intent, message: str) -> Dict[str, Any]:
        """Handle creation intents."""
        # Check if waiting for confirmation
        if self.conversation_state.confirmation_pending:
            is_confirmation, confirmed = self._handle_confirmation(message)
            if is_confirmation:
                if confirmed:
                    # Create entity
                    try:
                        if intent.entity == EntityType.CHATBOT:
                            result = self.chatbot_manager.create_chatbot(self.conversation_state.collected_data)
                        elif intent.entity == EntityType.HOTEL:
                            result = self.hotel_manager.create_hotel(self.conversation_state.collected_data)
                        
                        self.conversation_state.clear_state()
                        return {
                            "message": f"¡{intent.entity.value} creado exitosamente!",
                            "success": True,
                            "data": result.get("data", {})
                        }
                    except Exception as e:
                        self.conversation_state.clear_state()
                        return {
                            "message": self.response_generator.get_error_message("server", str(e)),
                            "success": False
                        }
                else:
                    self.conversation_state.clear_state()
                    return {
                        "message": "Proceso cancelado. ¿Hay algo más en lo que pueda ayudarle?",
                        "success": True
                    }
        
        # Start new process if none active
        if not self.conversation_state.active_process:
            required_fields = self.response_generator.entity_fields[intent.entity]["required"]
            self.conversation_state.start_process("create", intent.entity, required_fields)
            return {
                "message": self.response_generator.get_next_question(self.conversation_state),
                "success": True
            }
        
        # Process is active, collect data
        current_field = self.conversation_state.missing_fields[0]
        self.conversation_state.add_data(current_field, message)
        
        if self.conversation_state.is_process_complete():
            self.conversation_state.confirmation_pending = True
            return {
                "message": self.response_generator.get_confirmation_message(self.conversation_state),
                "success": True
            }
        
        return {
            "message": self.response_generator.get_next_question(self.conversation_state),
            "success": True
        }

    async def _handle_list_intent(self, intent) -> Dict[str, Any]:
        """Handle list intents."""
        try:
            if intent.entity == EntityType.CHATBOT:
                result = self.chatbot_manager.list_items()
            elif intent.entity == EntityType.HOTEL:
                result = self.hotel_manager.list_items()
            
            items = result.get("data", {}).get("items", [])
            message = f"Encontré {len(items)} {intent.entity.value}(s):\n\n"
            for item in items:
                message += f"• {item['name']}\n"
            
            return {
                "message": message,
                "success": True,
                "data": result.get("data", {})
            }
        except Exception as e:
            return {
                "message": self.response_generator.get_error_message("server", str(e)),
                "success": False
            }

    async def _handle_stats_intent(self, intent) -> Dict[str, Any]:
        """Handle statistics intents."""
        try:
            if intent.entity == EntityType.LEAD:
                result = self.lead_manager.get_lead_stats()
                return {
                    "message": "Estadísticas de leads actualizadas:",
                    "success": True,
                    "data": result.get("data", {})
                }
        except Exception as e:
            return {
                "message": self.response_generator.get_error_message("server", str(e)),
                "success": False
            }
        
    async def process_message(self, message: str) -> AdminChatResponse:
        """Process an incoming message and return a response."""
        try:
            # If in a process, handle current state
            if self.conversation_state.active_process:
                intent = self.conversation_state.last_intent
            else:
                # Detect new intent
                intent = self.intent_detector.detect_intent(message)
                self.conversation_state.last_intent = intent
            
            # Handle based on intent type
            if intent.type == IntentType.CREATE:
                response = await self._handle_create_intent(intent, message)
            elif intent.type == IntentType.LIST:
                response = await self._handle_list_intent(intent)
            elif intent.type == IntentType.STATS:
                response = await self._handle_stats_intent(intent)
            else:
                # Use LLM for unknown intents or general conversation
                self.conversation_history.append(HumanMessage(content=message))
                ai_message = self.llm(self.conversation_history)
                self.conversation_history.append(ai_message)
                response = {
                    "message": ai_message.content,
                    "success": True
                }
            
            return AdminChatResponse(
                message=response["message"],
                data=response.get("data", {}),
                success=response.get("success", True)
            )
            
        except Exception as e:
            return AdminChatResponse(
                message=self.response_generator.get_error_message("server", str(e)),
                success=False
            )
