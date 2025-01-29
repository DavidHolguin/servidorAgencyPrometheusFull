from typing import Dict, List, Optional, Any
from app.models.admin_schemas import AdminChatResponse
from app.models.ui_components import UIComponent, UIComponentType
from app.core.supabase import get_supabase_client

class BaseAssetManager:
    """Clase base para el manejo de activos administrativos"""
    
    def __init__(self, agency_id: str):
        self.agency_id = agency_id
        self.supabase = get_supabase_client()
        self.current_step = None
        self.form_data = {}
        
    async def validate_input(self, field: str, value: str) -> tuple[bool, str]:
        """Valida un campo de entrada"""
        raise NotImplementedError("Debe implementar validate_input")
        
    async def get_next_step(self, current_step: str) -> tuple[str, AdminChatResponse]:
        """Obtiene el siguiente paso del proceso"""
        raise NotImplementedError("Debe implementar get_next_step")
        
    async def process_step(self, step: str, message: str) -> AdminChatResponse:
        """Procesa un paso del formulario"""
        raise NotImplementedError("Debe implementar process_step")
        
    async def save_data(self) -> tuple[bool, str]:
        """Guarda los datos del formulario"""
        raise NotImplementedError("Debe implementar save_data")
        
    def reset(self):
        """Reinicia el estado del manager"""
        self.current_step = None
        self.form_data = {}
        
    def get_confirmation_component(self, id_prefix: str, label: str) -> Dict:
        """Obtiene un componente de confirmación estándar"""
        return UIComponent(
            type=UIComponentType.CONFIRMATION,
            id=f"{id_prefix}_confirmation",
            label=label,
            options=[
                {"value": "si", "label": "Sí"},
                {"value": "no", "label": "No"}
            ]
        ).dict()
        
    def get_text_input_component(self, id_prefix: str, label: str, required: bool = True, placeholder: str = "") -> Dict:
        """Obtiene un componente de entrada de texto estándar"""
        return UIComponent(
            type=UIComponentType.TEXT_INPUT,
            id=f"{id_prefix}_input",
            label=label,
            required=required,
            placeholder=placeholder
        ).dict()
        
    def get_select_component(self, id_prefix: str, label: str, options: List[Dict[str, str]]) -> Dict:
        """Obtiene un componente de selección estándar"""
        return UIComponent(
            type=UIComponentType.SELECT,
            id=f"{id_prefix}_select",
            label=label,
            options=options
        ).dict()
