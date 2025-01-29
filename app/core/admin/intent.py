"""Intent detection and conversation state management."""
from enum import Enum
from typing import List, Dict, Any, Optional

class IntentType(str, Enum):
    """Types of intents that can be detected."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    HELP = "help"
    CANCEL = "cancel"
    UNKNOWN = "unknown"

class EntityType(str, Enum):
    """Types of entities that can be managed."""
    CHATBOT = "chatbot"
    HOTEL = "hotel"
    ROOM = "room"
    PACKAGE = "package"
    UNKNOWN = "unknown"

class Intent:
    """Class to represent a detected intent."""
    def __init__(self, type: IntentType, entity: EntityType, data: Dict[str, Any] = None):
        self.type = type
        self.entity = entity
        self.data = data or {}

class ConversationState:
    """Class to manage conversation state."""
    
    def __init__(self):
        """Initialize conversation state."""
        self.conversation_history: List[Dict[str, str]] = []
        self.active_process: Optional[str] = None
        self.entity_type: Optional[EntityType] = None
        self.required_fields: List[str] = []
        self.collected_data: Dict[str, Any] = {}
        self.missing_fields: List[str] = []
        self.confirmation_pending: bool = False
        self.current_step: int = 0
        
    def add_to_history(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
    def start_process(self, process: str, entity: EntityType, required_fields: List[str]) -> None:
        """Start a new process."""
        self.active_process = process
        self.entity_type = entity
        self.required_fields = required_fields
        self.collected_data = {}
        self.missing_fields = required_fields.copy()
        self.confirmation_pending = False
        self.current_step = 0
        
    def add_data(self, field: str, value: Any) -> None:
        """Add collected data for a field."""
        self.collected_data[field] = value
        if field in self.missing_fields:
            self.missing_fields.remove(field)
        self.current_step += 1
        
    def is_process_complete(self) -> bool:
        """Check if all required fields are collected."""
        return len(self.missing_fields) == 0
        
    def clear_state(self) -> None:
        """Clear the current state."""
        self.active_process = None
        self.entity_type = None
        self.required_fields = []
        self.collected_data = {}
        self.missing_fields = []
        self.confirmation_pending = False
        self.current_step = 0

class IntentDetector:
    """Class to detect intents from user messages."""
    
    async def detect_intent(self, message: str, history: List[Dict[str, str]]) -> Intent:
        """
        Detect intent from user message.
        
        Args:
            message: User message
            history: Conversation history
            
        Returns:
            Intent: Detected intent
        """
        # Normalize message
        message = message.lower().strip()
        
        # Check for cancellation
        if any(word in message for word in ["cancelar", "cancel", "salir", "terminar"]):
            return Intent(IntentType.CANCEL, EntityType.UNKNOWN)
            
        # Check for help
        if any(word in message for word in ["ayuda", "help", "opciones", "options"]):
            return Intent(IntentType.HELP, EntityType.UNKNOWN)
            
        # Check for create intents
        if any(word in message for word in ["crear", "create", "nuevo", "new"]):
            if any(word in message for word in ["chatbot", "bot", "asistente"]):
                return Intent(IntentType.CREATE, EntityType.CHATBOT)
                
        # Check for list intents
        if any(word in message for word in ["listar", "list", "ver", "mostrar", "show"]):
            if any(word in message for word in ["chatbot", "bot", "asistente"]):
                return Intent(IntentType.LIST, EntityType.CHATBOT)
                
        # Default to unknown
        return Intent(IntentType.UNKNOWN, EntityType.UNKNOWN)

class ResponseGenerator:
    """Class to generate responses based on intents and state."""
    
    def get_error_message(self, error_type: str, details: str = "") -> str:
        """Get error message."""
        messages = {
            "server": "Lo siento, ha ocurrido un error en el servidor.",
            "validation": "Los datos proporcionados no son válidos.",
            "not_found": "No se encontró el recurso solicitado.",
            "unauthorized": "No tiene permisos para realizar esta acción."
        }
        return f"{messages.get(error_type, 'Error desconocido.')} {details}"
