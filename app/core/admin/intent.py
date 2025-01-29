"""Intent detection and conversation flow management."""
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import re
from langchain.schema import (
    SystemMessage,
    HumanMessage,
    AIMessage
)
from langchain_openai import ChatOpenAI

class IntentType(Enum):
    """Types of intents supported by the admin chatbot."""
    CREATE = "crear"
    UPDATE = "actualizar"
    DELETE = "eliminar"
    LIST = "listar"
    VIEW = "ver"
    STATS = "estadisticas"
    HELP = "ayuda"
    UNKNOWN = "desconocido"

class EntityType(Enum):
    """Types of entities that can be managed."""
    CHATBOT = "chatbot"
    HOTEL = "hotel"
    ROOM = "habitacion"
    LEAD = "lead"
    BOOKING = "reserva"
    LANDING = "landing"
    PACKAGE = "paquete"
    UNKNOWN = "desconocido"

@dataclass
class Intent:
    """Represents a detected intent."""
    type: IntentType
    entity: EntityType
    confidence: float
    params: Dict[str, Any]

class ConversationState:
    """Manages conversation state and flow."""
    
    def __init__(self):
        self.active_process: Optional[str] = None
        self.process_step: Optional[str] = None
        self.collected_data: Dict[str, Any] = {}
        self.missing_fields: List[str] = []
        self.current_entity: Optional[EntityType] = None
        self.last_intent: Optional[Intent] = None
        self.confirmation_pending: bool = False
        self.conversation_history: List[dict] = []
        
    def start_process(self, process: str, entity: EntityType, required_fields: List[str]):
        """Start a new process."""
        self.active_process = process
        self.current_entity = entity
        self.process_step = "collecting_data"
        self.collected_data = {}
        self.missing_fields = required_fields.copy()
        self.confirmation_pending = False
        
    def add_data(self, field: str, value: Any) -> bool:
        """Add data to the current process."""
        if field in self.missing_fields:
            self.collected_data[field] = value
            self.missing_fields.remove(field)
            return True
        return False
        
    def is_process_complete(self) -> bool:
        """Check if current process has all required data."""
        return len(self.missing_fields) == 0
        
    def clear_state(self):
        """Clear the conversation state."""
        self.active_process = None
        self.process_step = None
        self.collected_data = {}
        self.missing_fields = []
        self.current_entity = None
        self.last_intent = None
        self.confirmation_pending = False

    def add_to_history(self, role: str, content: str):
        """Add a message to conversation history."""
        self.conversation_history.append({"role": role, "content": content})

class IntentDetector:
    """Enhanced intent detection using LLM and pattern matching."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            temperature=0.7,
            model_name="gpt-4-turbo-preview"
        )
        self._compile_patterns()
        
    def _compile_patterns(self):
        """Compile regex patterns for intent detection."""
        self.patterns = {
            # Help patterns
            (IntentType.HELP, EntityType.UNKNOWN): [
                r"(?:que|qué|cuales|cuáles)\s+(?:puedes?|sabes?)\s+hacer",
                r"(?:ayuda|help|instrucciones|comandos)",
                r"(?:mostrar|ver)\s+(?:opciones|comandos|ayuda)",
                r"(?:como|cómo)\s+(?:funciona|trabajas|operas)"
            ],
            
            # Create patterns
            (IntentType.CREATE, EntityType.CHATBOT): [
                r"crear\s+(?:un\s+)?(?:nuevo\s+)?chatbot",
                r"nuevo\s+chatbot",
                r"agregar\s+(?:un\s+)?chatbot",
                r"configurar\s+(?:un\s+)?chatbot",
                r"implementar\s+(?:un\s+)?chatbot"
            ],
            
            # List patterns
            (IntentType.LIST, EntityType.CHATBOT): [
                r"(?:ver|mostrar|listar)\s+(?:los\s+)?chatbots?",
                r"lista\s+de\s+chatbots",
                r"chatbots\s+(?:disponibles|existentes)",
                r"(?:cuantos|cuántos)\s+chatbots?"
            ],
            
            # View patterns
            (IntentType.VIEW, EntityType.CHATBOT): [
                r"(?:ver|mostrar)\s+(?:el\s+)?chatbot\s+(?:con\s+id\s+)?([a-fA-F0-9-]{36})",
                r"detalles\s+(?:del\s+)?chatbot\s+(?:con\s+id\s+)?([a-fA-F0-9-]{36})",
                r"información\s+(?:del\s+)?chatbot\s+(?:con\s+id\s+)?([a-fA-F0-9-]{36})"
            ]
        }
        
        # Compile all patterns
        self.compiled_patterns = {
            key: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for key, patterns in self.patterns.items()
        }
        
    async def detect_intent(self, message: str, conversation_history: List[dict]) -> Intent:
        """
        Detect intent using a combination of pattern matching and LLM.
        The LLM helps understand context and disambiguate when patterns are unclear.
        """
        # First try pattern matching for common intents
        pattern_intent = self._detect_pattern_intent(message)
        if pattern_intent.confidence > 0.8:
            return pattern_intent
            
        # If pattern matching is not confident enough, use LLM
        return await self._detect_llm_intent(message, conversation_history)
        
    def _detect_pattern_intent(self, message: str) -> Intent:
        """Detect intent using regex patterns."""
        best_match = (IntentType.UNKNOWN, EntityType.UNKNOWN, 0.0, {})
        
        for (intent_type, entity_type), patterns in self.compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(message)
                if match:
                    # Calculate confidence based on match length and position
                    match_len = match.end() - match.start()
                    position_score = 1 - (match.start() / len(message))
                    confidence = (match_len / len(message) + position_score) / 2
                    
                    if confidence > best_match[2]:
                        params = self._extract_params(message, intent_type, entity_type)
                        best_match = (intent_type, entity_type, confidence, params)
        
        return Intent(
            type=best_match[0],
            entity=best_match[1],
            confidence=best_match[2],
            params=best_match[3]
        )
        
    async def _detect_llm_intent(self, message: str, conversation_history: List[dict]) -> Intent:
        """Use LLM to detect intent when pattern matching is not confident."""
        system_prompt = """You are an intent detection system for an administrative chatbot.
        Your task is to analyze the user's message and determine their intent.
        
        Available intents:
        - CREATE: User wants to create something
        - UPDATE: User wants to update something
        - DELETE: User wants to delete something
        - LIST: User wants to list items
        - VIEW: User wants to view details
        - STATS: User wants to see statistics
        - HELP: User needs help or information
        - UNKNOWN: Intent cannot be determined
        
        Available entities:
        - CHATBOT: Related to chatbot management
        - HOTEL: Related to hotel management
        - ROOM: Related to room management
        - LEAD: Related to lead management
        - BOOKING: Related to booking management
        - UNKNOWN: Entity cannot be determined
        
        Respond in JSON format:
        {
            "intent": "INTENT_TYPE",
            "entity": "ENTITY_TYPE",
            "confidence": 0.0-1.0,
            "params": {}
        }"""
        
        # Prepare conversation context
        messages = [SystemMessage(content=system_prompt)]
        
        # Add conversation history
        for msg in conversation_history[-3:]:  # Last 3 messages for context
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        
        # Add current message
        messages.append(HumanMessage(content=message))
        
        # Get LLM response
        response = await self.llm.agenerate([messages])
        result = response.generations[0][0].text
        
        try:
            # Parse LLM response
            import json
            data = json.loads(result)
            return Intent(
                type=IntentType[data["intent"]],
                entity=EntityType[data["entity"]],
                confidence=float(data["confidence"]),
                params=data["params"]
            )
        except:
            # If parsing fails, return unknown intent
            return Intent(
                type=IntentType.UNKNOWN,
                entity=EntityType.UNKNOWN,
                confidence=0.0,
                params={}
            )
            
    def _extract_params(self, message: str, intent_type: IntentType, entity_type: EntityType) -> Dict[str, Any]:
        """Extract parameters from message based on intent and entity type."""
        params = {}
        
        # Extract IDs
        id_pattern = r"(?:id|identificador)\s*[:=]?\s*([a-fA-F0-9-]{36})"
        id_match = re.search(id_pattern, message)
        if id_match:
            params["id"] = id_match.group(1)
            
        # Extract dates
        date_pattern = r"(?:fecha|desde|hasta)\s*[:=]?\s*(\d{4}-\d{2}-\d{2})"
        date_matches = re.finditer(date_pattern, message)
        dates = [m.group(1) for m in date_matches]
        if dates:
            params["dates"] = dates
            
        return params

class ResponseGenerator:
    """Generates appropriate responses based on conversation state."""
    
    def __init__(self):
        self.entity_fields = {
            EntityType.CHATBOT: {
                "required": [
                    "name",
                    "description",
                    "welcome_message",
                    "context",
                    "model_config"
                ],
                "optional": [
                    "icon",
                    "theme_color",
                    "custom_instructions"
                ],
                "field_names": {
                    "name": "nombre",
                    "description": "descripción",
                    "welcome_message": "mensaje de bienvenida",
                    "context": "contexto del chatbot",
                    "model_config": "configuración del modelo",
                    "icon": "ícono",
                    "theme_color": "color del tema",
                    "custom_instructions": "instrucciones personalizadas"
                }
            }
        }
        
    def get_next_question(self, state: ConversationState) -> str:
        """Get next question based on missing fields."""
        if not state.missing_fields:
            return self.get_confirmation_message(state)
            
        field = state.missing_fields[0]
        entity_config = self.entity_fields[state.current_entity]
        field_name = entity_config["field_names"].get(field, field)
        
        questions = {
            "name": f"¿Cuál será el nombre del {state.current_entity.value}?",
            "description": f"Por favor, proporcione una descripción clara del {state.current_entity.value}:",
            "welcome_message": "¿Cuál será el mensaje de bienvenida que mostrará el chatbot?",
            "context": "Describa el contexto o propósito principal del chatbot:",
            "model_config": "¿Qué modelo de lenguaje desea utilizar? (gpt-4, gpt-3.5-turbo):",
            "icon": "Puede proporcionar un ícono para el chatbot (opcional):",
            "theme_color": "¿Desea especificar un color tema? (ej: #FF5733, opcional):",
            "custom_instructions": "¿Hay instrucciones específicas para el comportamiento del chatbot? (opcional):"
        }
        
        return questions.get(field, f"Por favor, ingrese {field_name}:")
        
    def get_confirmation_message(self, state: ConversationState) -> str:
        """Get confirmation message with collected data."""
        entity_config = self.entity_fields[state.current_entity]
        field_names = entity_config["field_names"]
        
        message = f"He recopilado la siguiente información para el {state.current_entity.value}:\n\n"
        for field, value in state.collected_data.items():
            field_name = field_names.get(field, field)
            message += f"• {field_name}: {value}\n"
        
        message += "\n¿Desea confirmar la creación? (sí/no)"
        return message
        
    def get_error_message(self, error_type: str, details: str = "") -> str:
        """Get error message based on error type."""
        messages = {
            "validation": "Los datos proporcionados no son válidos.",
            "permission": "No tiene permisos para realizar esta acción.",
            "not_found": "No se encontró el recurso solicitado.",
            "server": "Ocurrió un error en el servidor.",
            "invalid_input": "El valor proporcionado no es válido.",
            "missing_field": "Falta un campo requerido.",
            "invalid_format": "El formato proporcionado no es válido."
        }
        
        base_message = messages.get(error_type, "Ocurrió un error inesperado.")
        return f"{base_message} {details}"
