from typing import Dict, List, Optional, Any, Tuple
from app.models.admin_schemas import AdminChatResponse
from app.models.ui_components import UIComponent, UIComponentType
from app.core.admin.base_manager import BaseAssetManager

class HotelManager(BaseAssetManager):
    """Manejador de operaciones CRUD para hoteles"""
    
    STEPS = {
        "CREATE": ["name", "description", "address", "category", "amenities", "images", "confirmation"],
        "EDIT": ["select", "name", "description", "address", "category", "amenities", "images", "confirmation"],
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
                message="Nombre del hotel:",
                components=[self.get_text_input_component("hotel", "Nombre")]
            )
        elif operation in ["EDIT", "DELETE"]:
            hotels = await self._get_hotels()
            if not hotels:
                return AdminChatResponse(
                    message="No hay hoteles disponibles para esta operación."
                )
                
            return AdminChatResponse(
                message=f"Seleccione el hotel que desea {'editar' if operation == 'EDIT' else 'eliminar'}:",
                components=[
                    UIComponent(
                        type=UIComponentType.SELECT,
                        id="hotel_select",
                        label="Hotel",
                        options=[{"value": str(h["id"]), "label": h["name"]} for h in hotels]
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
        elif field == "address":
            if len(value.strip()) < 10:
                return False, "La dirección debe tener al menos 10 caracteres."
        elif field == "category":
            valid_categories = ["1_star", "2_stars", "3_stars", "4_stars", "5_stars"]
            if value not in valid_categories:
                return False, "Categoría inválida."
        elif field == "select":
            try:
                hotel_id = int(value)
                hotels = await self._get_hotels()
                if not any(h["id"] == hotel_id for h in hotels):
                    return False, "Hotel no encontrado."
            except ValueError:
                return False, "ID de hotel inválido."
                
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
                    components=[self.get_confirmation_component("hotel", "¿Confirmar operación?")]
                )
                
        # Si hay más pasos, continuar al siguiente
        if current_index < len(current_steps) - 1:
            next_step = current_steps[current_index + 1]
            self.current_step = next_step
            
            if next_step == "name":
                return AdminChatResponse(
                    message="Nombre del hotel:",
                    components=[self.get_text_input_component("hotel", "Nombre")]
                )
            elif next_step == "description":
                return AdminChatResponse(
                    message="Descripción del hotel:",
                    components=[self.get_text_input_component("hotel", "Descripción")]
                )
            elif next_step == "address":
                return AdminChatResponse(
                    message="Dirección del hotel:",
                    components=[self.get_text_input_component("hotel", "Dirección")]
                )
            elif next_step == "category":
                return AdminChatResponse(
                    message="Categoría del hotel:",
                    components=[
                        UIComponent(
                            type=UIComponentType.SELECT,
                            id="hotel_category",
                            label="Categoría",
                            options=[
                                {"value": "1_star", "label": "⭐ 1 Estrella"},
                                {"value": "2_stars", "label": "⭐⭐ 2 Estrellas"},
                                {"value": "3_stars", "label": "⭐⭐⭐ 3 Estrellas"},
                                {"value": "4_stars", "label": "⭐⭐⭐⭐ 4 Estrellas"},
                                {"value": "5_stars", "label": "⭐⭐⭐⭐⭐ 5 Estrellas"}
                            ]
                        ).dict()
                    ]
                )
            elif next_step == "amenities":
                return AdminChatResponse(
                    message="Seleccione las comodidades del hotel:",
                    components=[
                        UIComponent(
                            type=UIComponentType.MULTI_SELECT,
                            id="hotel_amenities",
                            label="Comodidades",
                            options=[
                                {"value": "pool", "label": "Piscina"},
                                {"value": "gym", "label": "Gimnasio"},
                                {"value": "restaurant", "label": "Restaurante"},
                                {"value": "bar", "label": "Bar"},
                                {"value": "spa", "label": "Spa"},
                                {"value": "parking", "label": "Estacionamiento"},
                                {"value": "wifi", "label": "WiFi"},
                                {"value": "beach_access", "label": "Acceso a la playa"},
                                {"value": "conference_room", "label": "Sala de conferencias"},
                                {"value": "kids_club", "label": "Club infantil"}
                            ]
                        ).dict()
                    ]
                )
            elif next_step == "images":
                return AdminChatResponse(
                    message="Agregue imágenes del hotel (opcional):",
                    components=[
                        UIComponent(
                            type=UIComponentType.FILE_INPUT,
                            id="hotel_images",
                            label="Imágenes",
                            required=False,
                            multiple=True,
                            validation={
                                "accept": "image/*",
                                "maxSize": 5242880,
                                "maxFiles": 10
                            }
                        ).dict()
                    ]
                )
            elif next_step == "confirmation":
                operation_name = "crear" if self.operation == "CREATE" else "editar" if self.operation == "EDIT" else "eliminar"
                message = f"¿Desea {operation_name} el hotel con los siguientes datos?\n\n"
                
                if self.operation != "DELETE":
                    # Convertir categoría a estrellas
                    stars = "⭐" * int(self.form_data.get("category", "1_star")[0])
                    message += f"""Nombre: {self.form_data.get('name', '')}
Descripción: {self.form_data.get('description', '')}
Dirección: {self.form_data.get('address', '')}
Categoría: {stars}
Comodidades: {', '.join(self.form_data.get('amenities', []))}
Imágenes: {'Sí' if self.form_data.get('images') else 'No'}"""
                else:
                    hotels = await self._get_hotels()
                    hotel = next((h for h in hotels if str(h["id"]) == self.form_data["select"]), None)
                    if hotel:
                        message += f"Hotel: {hotel['name']}"
                
                return AdminChatResponse(
                    message=message,
                    components=[self.get_confirmation_component("hotel", f"¿{operation_name.capitalize()} hotel?")]
                )
                
        return AdminChatResponse(
            message="Ha ocurrido un error en el proceso. Por favor, intente nuevamente."
        )
        
    async def save_data(self) -> tuple[bool, str]:
        """Guarda los datos del formulario"""
        try:
            if self.operation == "CREATE":
                hotel_data = {
                    "agency_id": self.agency_id,
                    "name": self.form_data["name"],
                    "description": self.form_data["description"],
                    "address": self.form_data["address"],
                    "category": self.form_data["category"],
                    "amenities": self.form_data.get("amenities", []),
                    "images": self.form_data.get("images", [])
                }
                
                response = self.supabase.table("hotels").insert(hotel_data).execute()
                return True, "✅ Hotel creado exitosamente. ¿En qué más puedo ayudarle?"
                
            elif self.operation == "EDIT":
                hotel_data = {
                    "name": self.form_data["name"],
                    "description": self.form_data["description"],
                    "address": self.form_data["address"],
                    "category": self.form_data["category"],
                    "amenities": self.form_data.get("amenities", []),
                    "images": self.form_data.get("images", [])
                }
                
                response = self.supabase.table("hotels").update(hotel_data).eq("id", int(self.form_data["select"])).execute()
                return True, "✅ Hotel actualizado exitosamente. ¿En qué más puedo ayudarle?"
                
            elif self.operation == "DELETE":
                # Primero eliminar tipos de habitación asociados
                response = self.supabase.table("room_types").delete().eq("hotel_id", int(self.form_data["select"])).execute()
                # Luego eliminar el hotel
                response = self.supabase.table("hotels").delete().eq("id", int(self.form_data["select"])).execute()
                return True, "✅ Hotel y sus tipos de habitación eliminados exitosamente. ¿En qué más puedo ayudarle?"
                
        except Exception as e:
            print(f"Error al guardar hotel: {str(e)}")
            return False, "❌ Ha ocurrido un error al procesar la operación. Por favor, intente nuevamente."
            
    async def _get_hotels(self) -> List[Dict]:
        """Obtiene la lista de hoteles disponibles"""
        try:
            response = self.supabase.table("hotels").select("id, name").eq("agency_id", self.agency_id).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error al obtener hoteles: {str(e)}")
            return []
