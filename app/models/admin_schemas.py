from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field

class UIComponentType(str, Enum):
    TEXT_INPUT = "text_input"
    NUMBER_INPUT = "number_input"
    DATE_INPUT = "date_input"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    CONFIRMATION = "confirmation"
    FORM = "form"
    MESSAGE = "message"

class UIComponent(BaseModel):
    type: UIComponentType
    id: str
    label: str
    placeholder: Optional[str] = None
    required: bool = True
    options: Optional[List[Dict[str, str]]] = None
    validation: Optional[Dict[str, Any]] = None
    value: Optional[Any] = None

class AdminChatResponse(BaseModel):
    message: str = Field(..., description="Mensaje principal del chatbot")
    components: Optional[List[UIComponent]] = Field(
        default=None,
        description="Componentes UI para enriquecer la respuesta"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Contexto de la conversación y metadata"
    )
    action_required: bool = Field(
        default=False,
        description="Indica si se requiere una acción del usuario"
    )
    confirmation_required: bool = Field(
        default=False,
        description="Indica si se requiere confirmación del usuario"
    )
    confirmation_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Datos que requieren confirmación"
    )

class AdminChatRequest(BaseModel):
    message: str = Field(..., description="Mensaje del administrador")
    agency_id: str = Field(..., description="ID de la agencia")
    user_id: str = Field(..., description="ID del usuario administrador")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Contexto adicional para el mensaje"
    )
