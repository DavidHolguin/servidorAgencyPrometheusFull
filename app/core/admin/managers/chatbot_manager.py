from typing import Dict, List, Optional, Any, Tuple
from app.models.admin_schemas import AdminChatResponse
from app.models.ui_components import UIComponent, UIComponentType
from app.core.admin.base_manager import BaseAssetManager

class ChatbotManager(BaseAssetManager):
    """Manejador de operaciones CRUD para chatbots"""
    
    STEPS = {
        "CREATE": ["name", "description", "icon", "confirmation"],
        "EDIT": ["select", "name", "description", "icon", "confirmation"],
        "DELETE": ["select", "confirmation"]
    }
    
    def __init__(self, agency_id: str):
        super().__init__(agency_id)
        self.operation = None
        
    async def start_operation(self, operation: str) -> AdminChatResponse:
        """Inicia una operación CRUD"""
        self.operation = operation
        self.current_step = self.STEPS[operation][0]
        
        if operation == "CREATE":
            return AdminChatResponse(
                message="Nombre del chatbot:",
                components=[self.get_text_input_component("chatbot", "Nombre")]
            )
        elif operation in ["EDIT", "DELETE"]:
            chatbots = await self._get_chatbots()
            if not chatbots:
                return AdminChatResponse(
                    message="No hay chatbots disponibles para esta operación."
                )
            
            return AdminChatResponse(
                message=f"Seleccione el chatbot que desea {'editar' if operation == 'EDIT' else 'eliminar'}:",
                components=[
                    UIComponent(
                        type=UIComponentType.SELECT,
                        id="chatbot_select",
                        label="Chatbot",
                        options=[{"value": str(c["id"]), "label": c["name"]} for c in chatbots]
                    ).dict()
                ]
            )
            
    async def validate_input(self, field: str, value: str) -> tuple[bool, str]:
        """Valida un campo de entrada"""
        if field == "name":
            if len(value.strip()) < 3:
                return False, "El nombre debe tener al menos 3 caracteres."
        elif field == "description":
            if len(value.strip()) < 10:
                return False, "La descripción debe tener al menos 10 caracteres."
        elif field == "select":
            try:
                chatbot_id = int(value)
                chatbots = await self._get_chatbots()
                if not any(c["id"] == chatbot_id for c in chatbots):
                    return False, "Chatbot no encontrado."
            except ValueError:
                return False, "ID de chatbot inválido."
                
        return True, ""
        
    async def process_step(self, step: str, message: str) -> AdminChatResponse:
        """Procesa un paso del formulario"""
        # Validar entrada actual
        is_valid, error = await self.validate_input(step, message)
        if not is_valid:
            return AdminChatResponse(message=error)
            
        # Guardar dato actual
        self.form_data[step] = message
        
        # Obtener siguiente paso
        current_steps = self.STEPS[self.operation]
        current_index = current_steps.index(step)
        
        # Si es el último paso, procesar confirmación
        if step == "confirmation":
            if message.lower() in ['si', 'sí', 'yes']:
                success, result = await self.save_data()
                self.reset()
                return AdminChatResponse(
                    message=result,
                    action_required=False
                )
            elif message.lower() in ['no']:
                self.reset()
                return AdminChatResponse(
                    message="❌ Operación cancelada. ¿En qué más puedo ayudarle?",
                    action_required=False
                )
            else:
                return AdminChatResponse(
                    message="Por favor responda 'si' o 'no'.",
                    components=[self.get_confirmation_component("chatbot", "¿Confirmar operación?")]
                )
                
        # Si hay más pasos, continuar al siguiente
        if current_index < len(current_steps) - 1:
            next_step = current_steps[current_index + 1]
            self.current_step = next_step
            
            if next_step == "description":
                return AdminChatResponse(
                    message="Descripción del chatbot:",
                    components=[self.get_text_input_component("chatbot", "Descripción")]
                )
            elif next_step == "icon":
                return AdminChatResponse(
                    message="¿Desea agregar un ícono? (opcional)",
                    components=[
                        UIComponent(
                            type=UIComponentType.FILE_INPUT,
                            id="chatbot_icon",
                            label="Ícono",
                            required=False,
                            validation={
                                "accept": "image/*",
                                "maxSize": 2097152
                            }
                        ).dict()
                    ]
                )
            elif next_step == "confirmation":
                operation_name = "crear" if self.operation == "CREATE" else "editar" if self.operation == "EDIT" else "eliminar"
                message = f"¿Desea {operation_name} el chatbot con los siguientes datos?\n\n"
                
                if self.operation != "DELETE":
                    message += f"""Nombre: {self.form_data.get('name', '')}
Descripción: {self.form_data.get('description', '')}
Ícono: {'Sí' if self.form_data.get('icon') else 'No'}"""
                else:
                    chatbots = await self._get_chatbots()
                    chatbot = next((c for c in chatbots if str(c["id"]) == self.form_data["select"]), None)
                    if chatbot:
                        message += f"Chatbot: {chatbot['name']}"
                
                return AdminChatResponse(
                    message=message,
                    components=[self.get_confirmation_component("chatbot", f"¿{operation_name.capitalize()} chatbot?")]
                )
                
        return AdminChatResponse(
            message="Ha ocurrido un error en el proceso. Por favor, intente nuevamente."
        )
        
    async def save_data(self) -> tuple[bool, str]:
        """Guarda los datos del formulario"""
        try:
            if self.operation == "CREATE":
                chatbot_data = {
                    "agency_id": self.agency_id,
                    "name": self.form_data["name"],
                    "description": self.form_data["description"],
                    "icon_url": self.form_data.get("icon"),
                    "configuration": {
                        "welcome_message": f"¡Hola! Soy {self.form_data['name']}, ¿en qué puedo ayudarte?"
                    }
                }
                
                response = self.supabase.table("chatbots").insert(chatbot_data).execute()
                return True, "✅ Chatbot creado exitosamente. ¿En qué más puedo ayudarle?"
                
            elif self.operation == "EDIT":
                chatbot_data = {
                    "name": self.form_data["name"],
                    "description": self.form_data["description"],
                    "icon_url": self.form_data.get("icon")
                }
                
                response = self.supabase.table("chatbots").update(chatbot_data).eq("id", int(self.form_data["select"])).execute()
                return True, "✅ Chatbot actualizado exitosamente. ¿En qué más puedo ayudarle?"
                
            elif self.operation == "DELETE":
                response = self.supabase.table("chatbots").delete().eq("id", int(self.form_data["select"])).execute()
                return True, "✅ Chatbot eliminado exitosamente. ¿En qué más puedo ayudarle?"
                
        except Exception as e:
            print(f"Error al guardar chatbot: {str(e)}")
            return False, "❌ Ha ocurrido un error al procesar la operación. Por favor, intente nuevamente."
            
    async def _get_chatbots(self) -> List[Dict]:
        """Obtiene la lista de chatbots disponibles"""
        try:
            response = self.supabase.table("chatbots").select("id, name").eq("agency_id", self.agency_id).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error al obtener chatbots: {str(e)}")
            return []
