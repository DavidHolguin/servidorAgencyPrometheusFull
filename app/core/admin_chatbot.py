"""Admin chatbot manager module."""
from datetime import datetime
from typing import Dict, List, Optional, Any
from app.core.supabase import get_supabase_client
from app.models.admin_schemas import AdminChatResponse
from app.models.chatbot_schemas import ChatbotCreate, ChatbotResponse
from app.core.admin.intent import (
    IntentDetector,
    ResponseGenerator,
    ConversationState,
    IntentType,
    EntityType,
    Intent
)
from app.core.database import Database

class AdminChatbotManager:
    """Main class for handling administrative tasks through chatbot interface."""
    
    def __init__(self, agency_id: str, user_id: str):
        """Initialize the admin chatbot manager."""
        print("Inicializando AdminChatbotManager...")
        self.agency_id = agency_id
        self.user_id = user_id
        
        # Initialize components
        self.conversation_state = ConversationState()
        self.intent_detector = IntentDetector()
        self.response_generator = ResponseGenerator()
        self.db = Database()
        self.supabase = get_supabase_client()
        
        # Load agency data
        self.agency_data = self._load_agency_data()
        print(f"Datos de agencia cargados: {self.agency_data}")
        
        # Initialize conversation
        self._initialize_conversation()
        print("AdminChatbotManager inicializado correctamente")
        
    def _load_agency_data(self) -> dict:
        """Load agency data from database."""
        try:
            response = self.supabase.table("agencies").select("*").eq("id", self.agency_id).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            print(f"Error loading agency data: {str(e)}")
            return {}

    def _initialize_conversation(self) -> None:
        """Initialize the conversation with system prompt."""
        print("Inicializando conversación...")
        try:
            # Add system message to history
            self.conversation_state.add_to_history(
                "system",
                """Soy un asistente administrativo especializado en la gestión de chatbots y recursos turísticos.
                Puedo ayudarte con las siguientes tareas:
                
                1. Gestión de Chatbots:
                   - Crear nuevos chatbots
                   - Ver lista de chatbots
                   - Ver detalles de un chatbot
                   - Actualizar configuración
                   - Eliminar chatbots
                
                2. Gestión de Hoteles:
                   - Agregar nuevos hoteles
                   - Ver lista de hoteles
                   - Actualizar información
                   - Eliminar hoteles
                
                3. Gestión de Habitaciones:
                   - Agregar habitaciones
                   - Ver disponibilidad
                   - Actualizar precios
                   - Gestionar amenidades
                
                4. Gestión de Paquetes:
                   - Crear paquetes turísticos
                   - Ver paquetes disponibles
                   - Modificar paquetes
                   - Eliminar paquetes
                
                5. Análisis y Estadísticas:
                   - Ver métricas de chatbots
                   - Analizar conversiones
                   - Reportes de rendimiento
                
                ¿En qué puedo ayudarte hoy?"""
            )
            print("Conversación inicializada correctamente")
        except Exception as e:
            print(f"Error initializing conversation: {str(e)}")
            raise

    async def process_message(self, message: str) -> AdminChatResponse:
        """
        Process an incoming message and return an appropriate response.
        
        Args:
            message: The user's message
            
        Returns:
            AdminChatResponse: The chatbot's response
        """
        try:
            # Add message to conversation history
            self.conversation_state.add_to_history("user", message)
            
            # Convert conversation history to the format expected by LangChain
            history = [{"role": msg["role"], "content": msg["content"]} 
                      for msg in self.conversation_state.conversation_history]

            # Detect intent
            intent = await self.intent_detector.detect_intent(message, history)
            
            # If we're in an active process, handle it
            if self.conversation_state.active_process:
                return await self._handle_active_process(message, intent)

            # Handle new intents
            if intent.type == IntentType.CREATE:
                if intent.entity == EntityType.CHATBOT:
                    # Start chatbot creation process
                    required_fields = [
                        "name",
                        "description",
                        "welcome_message",
                        "context"
                    ]
                    self.conversation_state.start_process("create_chatbot", EntityType.CHATBOT, required_fields)
                    return AdminChatResponse(
                        message="Vamos a crear un nuevo chatbot. Por favor, ingrese el nombre del chatbot:",
                        success=True
                    )
                    
            elif intent.type == IntentType.LIST:
                if intent.entity == EntityType.CHATBOT:
                    chatbots = await self.db.list_chatbots(self.agency_id)
                    if not chatbots:
                        return AdminChatResponse(
                            message="No hay chatbots registrados. ¿Desea crear uno nuevo?",
                            success=True
                        )
                    response_text = "Chatbots disponibles:\n\n"
                    for bot in chatbots:
                        response_text += f"• {bot['name']}: {bot['description']}\n"
                    return AdminChatResponse(
                        message=response_text,
                        success=True,
                        data={"chatbots": chatbots}
                    )
                    
            # Default to help message
            return AdminChatResponse(
                message=("No estoy seguro de cómo ayudarte. Puedo:\n"
                         "• Crear un nuevo chatbot\n"
                         "• Listar chatbots existentes\n"
                         "• Ver detalles de un chatbot\n"
                         "• Actualizar un chatbot\n"
                         "• Eliminar un chatbot"),
                success=True
            )
            
        except Exception as e:
            return AdminChatResponse(
                message=self.response_generator.get_error_message("server", str(e)),
                success=False
            )

    async def _handle_active_process(self, message: str, intent: Intent) -> AdminChatResponse:
        """Handle messages during an active process."""
        
        # Check for process cancellation
        if message.lower() in ["cancelar", "cancel", "salir", "terminar"]:
            self.conversation_state.clear_state()
            return AdminChatResponse(
                message="Proceso cancelado. ¿En qué más puedo ayudarte?",
                success=True
            )

        # Handle chatbot creation process
        if self.conversation_state.active_process == "create_chatbot":
            # If we're waiting for confirmation
            if self.conversation_state.confirmation_pending:
                if any(word in message.lower() for word in ["si", "sí", "yes"]):
                    try:
                        # Prepare chatbot data
                        chatbot_data = self.conversation_state.collected_data.copy()
                        chatbot_data['agency_id'] = self.agency_id
                        
                        # Add default values if not provided
                        if 'model_config' not in chatbot_data:
                            chatbot_data['model_config'] = {
                                "model": "gpt-4-turbo-preview",
                                "temperature": 0.7,
                                "max_tokens": 1000
                            }
                        if 'theme_color' not in chatbot_data:
                            chatbot_data['theme_color'] = "#007bff"
                            
                        # Create chatbot using schema
                        chatbot = ChatbotCreate(**chatbot_data)
                        
                        # Add timestamp
                        now = datetime.now().isoformat()
                        data_to_insert = {
                            **chatbot.model_dump(),
                            'created_at': now,
                            'updated_at': now,
                            'is_active': True
                        }
                        
                        # Insert into database
                        response = self.supabase.table('chatbots').insert(data_to_insert).execute()
                        created_chatbot = response.data[0] if response.data else None
                        
                        if not created_chatbot:
                            raise Exception("No se pudo crear el chatbot")
                        
                        self.conversation_state.clear_state()
                        return AdminChatResponse(
                            message=f"¡Chatbot '{created_chatbot['name']}' creado exitosamente! ¿En qué más puedo ayudarte?",
                            success=True,
                            data={"chatbot": created_chatbot}
                        )
                    except Exception as e:
                        self.conversation_state.clear_state()
                        return AdminChatResponse(
                            message=f"Error al crear el chatbot: {str(e)}",
                            success=False
                        )
                elif any(word in message.lower() for word in ["no", "cancelar"]):
                    self.conversation_state.clear_state()
                    return AdminChatResponse(
                        message="Proceso cancelado. ¿En qué más puedo ayudarte?",
                        success=True
                    )
                else:
                    return AdminChatResponse(
                        message="Por favor confirme si desea crear el chatbot con los datos proporcionados (sí/no):",
                        success=True
                    )

            # Handle data collection
            if self.conversation_state.missing_fields:
                current_field = self.conversation_state.missing_fields[0]
                self.conversation_state.add_data(current_field, message)
                
                # If we have all required fields, ask for confirmation
                if self.conversation_state.is_process_complete():
                    self.conversation_state.confirmation_pending = True
                    confirmation_message = "Por favor confirme los siguientes datos para el chatbot:\n\n"
                    for field, value in self.conversation_state.collected_data.items():
                        confirmation_message += f"• {field}: {value}\n"
                    confirmation_message += "\n¿Desea crear el chatbot con estos datos? (sí/no):"
                    
                    return AdminChatResponse(
                        message=confirmation_message,
                        success=True
                    )
                
                # Otherwise, ask for the next field
                field_messages = {
                    "name": "Por favor, ingrese el nombre del chatbot:",
                    "description": "Por favor, ingrese una descripción del propósito del chatbot:",
                    "welcome_message": "¿Cuál será el mensaje de bienvenida que mostrará el chatbot?",
                    "context": "Por favor, proporcione el contexto o instrucciones específicas para el chatbot:"
                }
                
                next_field = self.conversation_state.missing_fields[0]
                return AdminChatResponse(
                    message=field_messages.get(next_field, f"Por favor, ingrese {next_field}:"),
                    success=True
                )

        return AdminChatResponse(
            message="Lo siento, ha ocurrido un error. ¿En qué puedo ayudarte?",
            success=False
        )
