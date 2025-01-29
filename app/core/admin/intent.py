"""Intent detection and conversation state management module."""
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import re

class IntentType(Enum):
    """Types of intents supported by the system."""
    CREATE = "create"
    LIST = "list"
    VIEW = "view"
    UPDATE = "update"
    DELETE = "delete"
    HELP = "help"
    UNKNOWN = "unknown"

class EntityType(Enum):
    """Types of entities that can be managed."""
    CHATBOT = "chatbot"
    HOTEL = "hotel"
    ROOM = "room"
    PACKAGE = "package"
    DESTINATION = "destination"
    UNKNOWN = "unknown"

@dataclass
class Intent:
    """Represents a detected intent with its parameters."""
    type: IntentType
    entity: EntityType
    confidence: float
    params: Dict[str, Any] = field(default_factory=dict)

class ConversationState:
    """Manages the state of an ongoing conversation."""
    
    def __init__(self):
        """Initialize conversation state."""
        self.active_process: Optional[str] = None
        self.current_entity: Optional[EntityType] = None
        self.collected_data: Dict[str, Any] = {}
        self.missing_fields: List[str] = []
        self.confirmation_pending: bool = False
        self.conversation_history: List[Dict[str, str]] = []

    def start_process(self, process_name: str, entity_type: EntityType, required_fields: List[str]) -> None:
        """Start a new process and initialize required fields."""
        self.active_process = process_name
        self.current_entity = entity_type
        self.collected_data = {}
        self.missing_fields = required_fields.copy()
        self.confirmation_pending = False

    def add_data(self, field: str, value: Any) -> None:
        """Add collected data and update missing fields."""
        self.collected_data[field] = value
        if field in self.missing_fields:
            self.missing_fields.remove(field)

    def is_process_complete(self) -> bool:
        """Check if all required fields are collected."""
        return len(self.missing_fields) == 0

    def clear_state(self) -> None:
        """Clear the current process state."""
        self.active_process = None
        self.current_entity = None
        self.collected_data = {}
        self.missing_fields = []
        self.confirmation_pending = False

    def add_to_history(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content
        })

    def get_current_state(self) -> Dict[str, Any]:
        """Get the current state of the conversation."""
        return {
            "active_process": self.active_process,
            "current_entity": self.current_entity.value if self.current_entity else None,
            "collected_data": self.collected_data,
            "missing_fields": self.missing_fields,
            "confirmation_pending": self.confirmation_pending
        }

class IntentDetector:
    """Detects user intents from messages."""

    def __init__(self):
        """Initialize intent patterns."""
        self.patterns = {
            # Chatbot patterns
            (IntentType.CREATE, EntityType.CHATBOT): [
                r"crear(?:\s+un)?\s+(?:nuevo\s+)?chatbot",
                r"nuevo\s+chatbot",
                r"agregar\s+(?:un\s+)?chatbot",
                r"configurar\s+(?:un\s+)?(?:nuevo\s+)?chatbot"
            ],
            (IntentType.LIST, EntityType.CHATBOT): [
                r"ver\s+(?:la\s+)?lista\s+(?:de\s+)?chatbots?",
                r"mostrar\s+(?:los\s+)?chatbots",
                r"listar\s+chatbots",
                r"qué\s+chatbots\s+(?:hay|tengo|existen)"
            ],
            (IntentType.VIEW, EntityType.CHATBOT): [
                r"ver\s+(?:el\s+)?chatbot\s+(?:con\s+id\s+)?([a-zA-Z0-9-]+)",
                r"mostrar\s+(?:el\s+)?chatbot\s+(?:con\s+id\s+)?([a-zA-Z0-9-]+)",
                r"detalles\s+(?:del\s+)?chatbot\s+(?:con\s+id\s+)?([a-zA-Z0-9-]+)"
            ],
            (IntentType.UPDATE, EntityType.CHATBOT): [
                r"editar\s+(?:el\s+)?chatbot\s+(?:con\s+id\s+)?([a-zA-Z0-9-]+)",
                r"modificar\s+(?:el\s+)?chatbot\s+(?:con\s+id\s+)?([a-zA-Z0-9-]+)",
                r"actualizar\s+(?:el\s+)?chatbot\s+(?:con\s+id\s+)?([a-zA-Z0-9-]+)"
            ],
            (IntentType.DELETE, EntityType.CHATBOT): [
                r"eliminar\s+(?:el\s+)?chatbot\s+(?:con\s+id\s+)?([a-zA-Z0-9-]+)",
                r"borrar\s+(?:el\s+)?chatbot\s+(?:con\s+id\s+)?([a-zA-Z0-9-]+)",
                r"quitar\s+(?:el\s+)?chatbot\s+(?:con\s+id\s+)?([a-zA-Z0-9-]+)"
            ],
            
            # Hotel patterns
            (IntentType.CREATE, EntityType.HOTEL): [
                r"crear\s+(?:un\s+)?(?:nuevo\s+)?hotel",
                r"nuevo\s+hotel",
                r"agregar\s+(?:un\s+)?hotel",
                r"configurar\s+(?:un\s+)?(?:nuevo\s+)?hotel"
            ],
            (IntentType.LIST, EntityType.HOTEL): [
                r"ver\s+(?:la\s+)?lista\s+(?:de\s+)?hotele?s",
                r"mostrar\s+(?:los\s+)?hotele?s",
                r"listar\s+hotele?s",
                r"qué\s+hotele?s\s+(?:hay|tengo|existen)"
            ],
            
            # Help patterns
            (IntentType.HELP, EntityType.UNKNOWN): [
                r"ayuda",
                r"help",
                r"qué\s+puedo\s+hacer",
                r"opciones",
                r"comandos",
                r"instrucciones"
            ]
        }

    async def detect_intent(self, message: str, conversation_history: List[Dict[str, str]]) -> Intent:
        """
        Detect the intent from a message using regex patterns and conversation context.
        
        Args:
            message: The user's message
            conversation_history: List of previous messages in the conversation
            
        Returns:
            Intent: The detected intent with its parameters
        """
        message = message.lower().strip()
        
        # Check for confirmation/cancellation in active process
        if any(word in message for word in ["si", "sí", "yes", "no", "cancelar", "terminar"]):
            # Get the last assistant message
            last_assistant_msg = next((msg["content"] for msg in reversed(conversation_history) 
                                    if msg["role"] == "assistant"), "")
            
            # If it was asking for confirmation
            if "confirmar" in last_assistant_msg.lower() or "confirme" in last_assistant_msg.lower():
                return Intent(
                    type=IntentType.CREATE if "si" in message or "sí" in message or "yes" in message 
                          else IntentType.UNKNOWN,
                    entity=EntityType.UNKNOWN,
                    confidence=1.0,
                    params={"confirmation": "yes" if "si" in message or "sí" in message or "yes" in message else "no"}
                )

        # Check each pattern
        for (intent_type, entity_type), patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    params = {}
                    # Extract ID if present in the match groups
                    if match.groups():
                        params["id"] = match.group(1)
                    
                    return Intent(
                        type=intent_type,
                        entity=entity_type,
                        confidence=1.0,
                        params=params
                    )

        # If no pattern matches, try to infer from context
        return self._infer_from_context(message, conversation_history)

    def _infer_from_context(self, message: str, conversation_history: List[Dict[str, str]]) -> Intent:
        """Infer intent from conversation context when no pattern matches."""
        # Get the last assistant message
        last_assistant_msg = next((msg["content"] for msg in reversed(conversation_history) 
                                if msg["role"] == "assistant"), "")
        
        # If the last message was asking for a chatbot name
        if "nombre del chatbot" in last_assistant_msg.lower():
            return Intent(
                type=IntentType.CREATE,
                entity=EntityType.CHATBOT,
                confidence=0.8,
                params={"name": message}
            )
        
        # If the last message was asking for a chatbot description
        if "descripción" in last_assistant_msg.lower() and "chatbot" in last_assistant_msg.lower():
            return Intent(
                type=IntentType.CREATE,
                entity=EntityType.CHATBOT,
                confidence=0.8,
                params={"description": message}
            )
        
        # Default to unknown intent
        return Intent(
            type=IntentType.UNKNOWN,
            entity=EntityType.UNKNOWN,
            confidence=0.0
        )

class ResponseGenerator:
    """Generates appropriate responses based on intent and conversation state."""
    
    def __init__(self):
        """Initialize response templates and entity fields."""
        self.entity_fields = {
            EntityType.CHATBOT: {
                "required": ["name", "description"],
                "optional": ["icon_url", "welcome_message"]
            },
            EntityType.HOTEL: {
                "required": ["name", "description", "address", "city", "country"],
                "optional": ["rating", "amenities"]
            }
        }
        
        self.error_messages = {
            "not_found": "No se encontró el recurso solicitado.",
            "invalid_input": "La entrada proporcionada no es válida.",
            "server": "Ocurrió un error en el servidor: {}",
            "permission": "No tiene permisos para realizar esta operación.",
            "process_active": "Ya hay un proceso activo. ¿Desea cancelarlo?"
        }

    def get_next_question(self, state: ConversationState) -> str:
        """Get the next question based on the current state."""
        if not state.missing_fields:
            return "¿Desea confirmar la operación?"
            
        current_field = state.missing_fields[0]
        
        # Field-specific questions
        questions = {
            "name": "Por favor, ingrese el nombre:",
            "description": "Por favor, ingrese una descripción:",
            "address": "Por favor, ingrese la dirección:",
            "city": "Por favor, ingrese la ciudad:",
            "country": "Por favor, ingrese el país:",
            "welcome_message": "Por favor, ingrese el mensaje de bienvenida:",
            "icon_url": "Por favor, proporcione la URL del ícono (opcional):"
        }
        
        return questions.get(current_field, f"Por favor, ingrese {current_field}:")

    def get_confirmation_message(self, state: ConversationState) -> str:
        """Generate a confirmation message for the current process."""
        entity_name = state.current_entity.value if state.current_entity else "recurso"
        
        message = f"Por favor confirme los siguientes datos para crear el {entity_name}:\n\n"
        
        for field, value in state.collected_data.items():
            message += f"• {field.capitalize()}: {value}\n"
        
        message += "\n¿Desea confirmar la operación? (sí/no)"
        
        return message

    def get_error_message(self, error_type: str, details: str = "") -> str:
        """Get an appropriate error message."""
        template = self.error_messages.get(error_type, "Error desconocido")
        return template.format(details) if "{}" in template else template
