from typing import Dict, List, Optional, Any, Tuple
from app.models.admin_schemas import AdminChatResponse
from app.models.ui_components import UIComponent, UIComponentType
from app.core.admin.base_manager import BaseAssetManager

class ChatbotManager(BaseAssetManager):
    """Manejador de operaciones CRUD para chatbots"""
    
    STEPS = {
        "CREATE": [
            "name",
            "description",
            "purpose",
            "welcome_message",
            "personality_tone",
            "personality_formality",
            "personality_emoji",
            "key_points",
            "special_instructions",
            "example_qa",
            "icon",
            "confirmation"
        ],
        "EDIT": [
            "select",
            "name",
            "description",
            "purpose",
            "welcome_message",
            "personality_tone",
            "personality_formality",
            "personality_emoji",
            "key_points",
            "special_instructions",
            "example_qa",
            "icon",
            "confirmation"
        ],
        "DELETE": ["select", "confirmation"]
    }
    
    def __init__(self, agency_id: str):
        super().__init__(agency_id)
        self.operation = None
        self.form_data = {}
    
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
        next_step = self._get_next_step(step)
        
        # Si es el último paso, procesar confirmación
        if step == "confirmation":
            if message.lower() in ['si', 'sí', 'yes']:
                success, result = await self.save_data()
                self.reset()
                return AdminChatResponse(
                    message=result,
                    action_required=False
                )
            else:
                self.reset()
                return AdminChatResponse(
                    message="Operación cancelada",
                    action_required=False
                )
        
        # Preparar el siguiente paso
        return self._prepare_step_response(next_step)
    
    def _prepare_step_response(self, step: str) -> AdminChatResponse:
        """Prepara la respuesta para el siguiente paso"""
        prompts = {
            "name": "Nombre del chatbot:",
            "description": "Descripción del chatbot:",
            "purpose": "¿Cuál es el propósito principal del chatbot? (ej: ventas, soporte, información)",
            "welcome_message": "Mensaje de bienvenida para los usuarios:",
            "personality_tone": "Selecciona el tono de comunicación:",
            "personality_formality": "Nivel de formalidad:",
            "personality_emoji": "Uso de emojis:",
            "key_points": "Ingresa los puntos clave que el chatbot debe considerar (uno por línea):",
            "special_instructions": "Instrucciones especiales para el chatbot (una por línea):",
            "example_qa": "Ejemplos de preguntas y respuestas (formato: P: pregunta | R: respuesta):",
            "icon": "URL del ícono del chatbot (opcional):",
            "confirmation": "¿Confirmas la creación del chatbot? (si/no)"
        }
        
        components = []
        if step == "personality_tone":
            components = [
                self.get_select_component("tone", "Tono", [
                    {"value": "profesional", "label": "Profesional"},
                    {"value": "amigable", "label": "Amigable"},
                    {"value": "casual", "label": "Casual"},
                    {"value": "formal", "label": "Formal"}
                ])
            ]
        elif step == "personality_formality":
            components = [
                self.get_select_component("formality", "Formalidad", [
                    {"value": "muy_formal", "label": "Muy Formal"},
                    {"value": "formal", "label": "Formal"},
                    {"value": "semiformal", "label": "Semi-formal"},
                    {"value": "informal", "label": "Informal"}
                ])
            ]
        elif step == "personality_emoji":
            components = [
                self.get_select_component("emoji", "Uso de Emojis", [
                    {"value": "ninguno", "label": "Sin emojis"},
                    {"value": "moderado", "label": "Uso moderado"},
                    {"value": "frecuente", "label": "Uso frecuente"}
                ])
            ]
        else:
            components = [self.get_text_input_component(step, prompts[step])]
        
        return AdminChatResponse(
            message=prompts[step],
            components=components
        )
    
    async def save_data(self) -> Tuple[bool, str]:
        """Guarda los datos del chatbot"""
        try:
            # Construir la personalidad
            personality = {
                "tone": self.form_data.get("personality_tone"),
                "formality_level": self.form_data.get("personality_formality"),
                "emoji_usage": self.form_data.get("personality_emoji"),
                "language_style": "claro y conciso"
            }
            
            # Procesar puntos clave y ejemplos
            key_points = [point.strip() for point in self.form_data.get("key_points", "").split("\n") if point.strip()]
            special_instructions = [instr.strip() for instr in self.form_data.get("special_instructions", "").split("\n") if instr.strip()]
            
            # Procesar ejemplos Q&A
            example_qa = []
            for line in self.form_data.get("example_qa", "").split("\n"):
                if "|" in line:
                    q, a = line.split("|")
                    q = q.replace("P:", "").strip()
                    a = a.replace("R:", "").strip()
                    if q and a:
                        example_qa.append({"question": q, "answer": a})
            
            # Crear el objeto chatbot
            chatbot_data = {
                "name": self.form_data.get("name"),
                "description": self.form_data.get("description"),
                "purpose": self.form_data.get("purpose"),
                "welcome_message": self.form_data.get("welcome_message"),
                "personality": personality,
                "key_points": key_points,
                "special_instructions": special_instructions,
                "example_qa": example_qa,
                "icon_url": self.form_data.get("icon"),
                "agency_id": self.agency_id,
                "configuration": {
                    "temperature": 0.7,
                    "model": "gpt-4-turbo-preview",
                    "max_tokens": 1000
                },
                "response_weights": {
                    "key_points_weight": 0.3,
                    "example_qa_weight": 0.4,
                    "special_instructions_weight": 0.5
                }
            }
            
            if self.operation == "CREATE":
                result = await self.db.create_chatbot(chatbot_data)
            else:
                result = await self.db.update_chatbot(self.form_data["select"], chatbot_data)
            
            return True, f"Chatbot {'creado' if self.operation == 'CREATE' else 'actualizado'} exitosamente"
            
        except Exception as e:
            print(f"Error saving chatbot: {str(e)}")
            return False, f"Error al {'crear' if self.operation == 'CREATE' else 'actualizar'} el chatbot"
    
    def _get_next_step(self, current_step: str) -> str:
        """Obtiene el siguiente paso en el proceso"""
        steps = self.STEPS[self.operation]
        current_index = steps.index(current_step)
        if current_index < len(steps) - 1:
            return steps[current_index + 1]
        return "confirmation"

    async def _get_chatbots(self) -> List[Dict]:
        """Obtiene la lista de chatbots disponibles"""
        try:
            response = self.supabase.table("chatbots").select("id, name").eq("agency_id", self.agency_id).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error al obtener chatbots: {str(e)}")
            return []
