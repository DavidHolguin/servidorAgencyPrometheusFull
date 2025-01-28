from typing import Dict, List, Optional, Any
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
    FILE_INPUT = "file_input"

class UIComponent(BaseModel):
    type: UIComponentType
    id: str
    label: str
    placeholder: Optional[str] = None
    required: bool = True
    options: Optional[List[Dict[str, str]]] = None
    validation: Optional[Dict[str, Any]] = None
    value: Optional[Any] = None
