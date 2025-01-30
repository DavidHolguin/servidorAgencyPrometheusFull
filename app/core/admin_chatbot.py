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
            
            # Check if we have chatbot data in the message
            if any(key in message.lower() for key in ['nombre:', 'descripción:', 'mensaje de bienvenida:', 'contexto:']):
                return await self._handle_chatbot_creation(message)
            
            # If we're in an active process, handle it
            if self.conversation_state.active_process:
                return await self._handle_active_process(message, intent)

            # Handle new intents
            if intent.type == IntentType.CREATE:
                if intent.entity == EntityType.CHATBOT:
                    self.conversation_state.start_process("create_chatbot", EntityType.CHATBOT, [])
                    return AdminChatResponse(
                        message=("Por favor proporcione la siguiente información para crear el chatbot "
                                "en este formato:\n\n"
                                "Nombre: [nombre del chatbot]\n"
                                "Descripción: [descripción del chatbot]\n"
                                "Mensaje de bienvenida: [mensaje]\n"
                                "Contexto: [instrucciones específicas]\n\n"
                                "Por ejemplo:\n"
                                "Nombre: Asistente de Viajes\n"
                                "Descripción: Chatbot para ayudar a reservar viajes\n"
                                "Mensaje de bienvenida: ¡Hola! Soy tu asistente de viajes\n"
                                "Contexto: Ayudar a los usuarios a encontrar y reservar viajes"),
                        success=True
                    )
            elif intent.type == IntentType.UPDATE:
                if intent.entity == EntityType.CHATBOT:
                    chatbots = await self.db.list_chatbots(self.agency_id)
                    if not chatbots:
                        return AdminChatResponse(
                            message="No hay chatbots registrados para modificar.",
                            success=True
                        )
                    
                    response_text = ("Los campos que puedes modificar son:\n\n"
                                   "• name (Nombre del chatbot)\n"
                                   "• description (Descripción)\n"
                                   "• welcome_message (Mensaje de bienvenida)\n"
                                   "• context (Contexto/instrucciones)\n"
                                   "• model_config (Configuración del modelo)\n"
                                   "• theme_color (Color del tema)\n\n"
                                   "Chatbots disponibles:\n\n")
                    
                    for bot in chatbots:
                        response_text += f"• {bot['name']}: {bot['description']}\n"
                    
                    response_text += ("\n¿Qué chatbot y qué campo deseas modificar? "
                                    "Por favor responde en el formato: "
                                    "'Modificar [nombre del chatbot] campo [nombre del campo] valor [nuevo valor]'")
                    
                    return AdminChatResponse(
                        message=response_text,
                        success=True,
                        data={"chatbots": chatbots}
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
            try:
                # Parse the input message to extract chatbot information
                lines = message.split('\n')
                chatbot_data = {}
                
                for line in lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip()
                        
                        if key == 'nombre':
                            chatbot_data['name'] = value
                        elif key == 'descripción':
                            chatbot_data['description'] = value
                        elif key == 'mensaje de bienvenida':
                            chatbot_data['welcome_message'] = value
                        elif key == 'contexto':
                            chatbot_data['context'] = value
                
                # Validate required fields
                required_fields = ['name', 'description', 'welcome_message', 'context']
                missing_fields = [field for field in required_fields if field not in chatbot_data]
                
                if missing_fields:
                    return AdminChatResponse(
                        message=f"Falta la siguiente información requerida: {', '.join(missing_fields)}. "
                               "Por favor proporciona todos los campos necesarios.",
                        success=False
                    )
                
                # Add default values
                chatbot_data['agency_id'] = self.agency_id
                chatbot_data['model_config'] = {
                    "model": "gpt-4-turbo-preview",
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
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
                return AdminChatResponse(
                    message=f"Error al procesar la información del chatbot: {str(e)}. "
                           "Por favor verifica el formato e intenta nuevamente.",
                    success=False
                )
        
        elif self.conversation_state.active_process == "update_chatbot":
            try:
                # Parse update command
                parts = message.lower().split()
                if len(parts) < 6 or 'modificar' not in parts or 'campo' not in parts or 'valor' not in parts:
                    return AdminChatResponse(
                        message="Formato incorrecto. Usa: 'Modificar [nombre del chatbot] campo [nombre del campo] valor [nuevo valor]'",
                        success=False
                    )
                
                # Extract chatbot name and field to update
                bot_name_idx = parts.index('modificar') + 1
                field_idx = parts.index('campo') + 1
                value_idx = parts.index('valor') + 1
                
                bot_name = ' '.join(parts[bot_name_idx:parts.index('campo')])
                field = parts[field_idx]
                new_value = ' '.join(parts[value_idx:])
                
                # Validate field name
                valid_fields = ['name', 'description', 'welcome_message', 'context', 'model_config', 'theme_color']
                if field not in valid_fields:
                    return AdminChatResponse(
                        message=f"Campo inválido. Los campos válidos son: {', '.join(valid_fields)}",
                        success=False
                    )
                
                # Update chatbot in database
                now = datetime.now().isoformat()
                update_data = {
                    field: new_value,
                    'updated_at': now
                }
                
                response = self.supabase.table('chatbots').update(update_data).eq('name', bot_name).execute()
                updated_chatbot = response.data[0] if response.data else None
                
                if not updated_chatbot:
                    raise Exception(f"No se encontró el chatbot '{bot_name}'")
                
                self.conversation_state.clear_state()
                return AdminChatResponse(
                    message=f"¡Chatbot '{bot_name}' actualizado exitosamente! Campo '{field}' modificado a '{new_value}'",
                    success=True,
                    data={"chatbot": updated_chatbot}
                )
                
            except Exception as e:
                return AdminChatResponse(
                    message=f"Error al actualizar el chatbot: {str(e)}",
                    success=False
                )

        return AdminChatResponse(
            message="Lo siento, ha ocurrido un error. ¿En qué puedo ayudarte?",
            success=False
        )

    async def _handle_chatbot_creation(self, message: str) -> AdminChatResponse:
        """Handle the creation of a new chatbot from user input."""
        try:
            # Parse the input message to extract chatbot information
            chatbot_data = {}
            
            # Handle both newline and space-separated formats
            if '\n' in message:
                lines = message.split('\n')
            else:
                # Split by field markers if it's all in one line
                message = message.replace('Nombre:', '\nNombre:')
                message = message.replace('Descripción:', '\nDescripción:')
                message = message.replace('Mensaje de bienvenida:', '\nMensaje de bienvenida:')
                message = message.replace('Contexto:', '\nContexto:')
                lines = message.split('\n')
            
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == 'nombre':
                        chatbot_data['name'] = value
                    elif key == 'descripción':
                        chatbot_data['description'] = value
                    elif key == 'mensaje de bienvenida':
                        chatbot_data['welcome_message'] = value
                    elif key == 'contexto':
                        chatbot_data['context'] = value
            
            # Validate required fields
            required_fields = ['name', 'description', 'welcome_message', 'context']
            missing_fields = [field for field in required_fields if field not in chatbot_data]
            
            if missing_fields:
                return AdminChatResponse(
                    message=f"Falta la siguiente información requerida: {', '.join(missing_fields)}. "
                           "Por favor proporciona todos los campos necesarios.",
                    success=False
                )
            
            # Add default values
            chatbot_data['agency_id'] = self.agency_id
            chatbot_data['model_config'] = {
                "model": "gpt-4-turbo-preview",
                "temperature": 0.7,
                "max_tokens": 1000
            }
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
            return AdminChatResponse(
                message=f"Error al procesar la información del chatbot: {str(e)}. "
                       "Por favor verifica el formato e intenta nuevamente.",
                success=False
            )
