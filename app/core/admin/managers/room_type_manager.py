from typing import Dict, List, Optional, Any, Tuple
from app.models.admin_schemas import AdminChatResponse
from app.models.ui_components import UIComponent, UIComponentType
from app.core.admin.base_manager import BaseAssetManager

class RoomTypeManager(BaseAssetManager):
    """Manejador de operaciones CRUD para tipos de habitación"""
    
    STEPS = {
        "CREATE": ["hotel", "name", "description", "capacity", "price", "amenities", "images", "confirmation"],
        "EDIT": ["select", "name", "description", "capacity", "price", "amenities", "images", "confirmation"],
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
            hotels = await self._get_hotels()
            if not hotels:
                return AdminChatResponse(
                    message="No hay hoteles disponibles. Primero debe crear un hotel."
                )
                
            return AdminChatResponse(
                message="Seleccione el hotel al que pertenecerá el tipo de habitación:",
                components=[
                    UIComponent(
                        type=UIComponentType.SELECT,
                        id="hotel_select",
                        label="Hotel",
                        options=[{"value": str(h["id"]), "label": h["name"]} for h in hotels]
                    ).dict()
                ]
            )
            
        elif operation in ["EDIT", "DELETE"]:
            room_types = await self._get_room_types()
            if not room_types:
                return AdminChatResponse(
                    message="No hay tipos de habitación disponibles para esta operación."
                )
                
            return AdminChatResponse(
                message=f"Seleccione el tipo de habitación que desea {'editar' if operation == 'EDIT' else 'eliminar'}:",
                components=[
                    UIComponent(
                        type=UIComponentType.SELECT,
                        id="room_type_select",
                        label="Tipo de Habitación",
                        options=[{"value": str(r["id"]), "label": f"{r['hotel_name']} - {r['name']}"} for r in room_types]
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
        elif field == "capacity":
            try:
                capacity = int(value)
                if capacity < 1 or capacity > 10:
                    return False, "La capacidad debe estar entre 1 y 10 personas."
            except ValueError:
                return False, "La capacidad debe ser un número entero."
        elif field == "price":
            try:
                price = float(value)
                if price <= 0:
                    return False, "El precio debe ser mayor a 0."
            except ValueError:
                return False, "El precio debe ser un número válido."
        elif field in ["hotel", "select"]:
            try:
                item_id = int(value)
                if field == "hotel":
                    hotels = await self._get_hotels()
                    if not any(h["id"] == item_id for h in hotels):
                        return False, "Hotel no encontrado."
                else:
                    room_types = await self._get_room_types()
                    if not any(r["id"] == item_id for r in room_types):
                        return False, "Tipo de habitación no encontrado."
            except ValueError:
                return False, f"ID de {'hotel' if field == 'hotel' else 'tipo de habitación'} inválido."
                
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
                    components=[self.get_confirmation_component("room_type", "¿Confirmar operación?")]
                )
                
        # Si hay más pasos, continuar al siguiente
        if current_index < len(current_steps) - 1:
            next_step = current_steps[current_index + 1]
            self.current_step = next_step
            
            if next_step == "name":
                return AdminChatResponse(
                    message="Nombre del tipo de habitación:",
                    components=[self.get_text_input_component("room_type", "Nombre")]
                )
            elif next_step == "description":
                return AdminChatResponse(
                    message="Descripción del tipo de habitación:",
                    components=[self.get_text_input_component("room_type", "Descripción")]
                )
            elif next_step == "capacity":
                return AdminChatResponse(
                    message="Capacidad de la habitación (número de personas):",
                    components=[
                        UIComponent(
                            type=UIComponentType.NUMBER_INPUT,
                            id="room_type_capacity",
                            label="Capacidad",
                            validation={
                                "min": 1,
                                "max": 10,
                                "step": 1
                            }
                        ).dict()
                    ]
                )
            elif next_step == "price":
                return AdminChatResponse(
                    message="Precio por noche:",
                    components=[
                        UIComponent(
                            type=UIComponentType.NUMBER_INPUT,
                            id="room_type_price",
                            label="Precio",
                            validation={
                                "min": 0,
                                "step": 0.01
                            }
                        ).dict()
                    ]
                )
            elif next_step == "amenities":
                return AdminChatResponse(
                    message="Seleccione las comodidades de la habitación:",
                    components=[
                        UIComponent(
                            type=UIComponentType.MULTI_SELECT,
                            id="room_type_amenities",
                            label="Comodidades",
                            options=[
                                {"value": "wifi", "label": "WiFi"},
                                {"value": "tv", "label": "TV"},
                                {"value": "ac", "label": "Aire Acondicionado"},
                                {"value": "minibar", "label": "Minibar"},
                                {"value": "safe", "label": "Caja Fuerte"},
                                {"value": "balcony", "label": "Balcón"},
                                {"value": "jacuzzi", "label": "Jacuzzi"}
                            ]
                        ).dict()
                    ]
                )
            elif next_step == "images":
                return AdminChatResponse(
                    message="Agregue imágenes de la habitación (opcional):",
                    components=[
                        UIComponent(
                            type=UIComponentType.FILE_INPUT,
                            id="room_type_images",
                            label="Imágenes",
                            required=False,
                            multiple=True,
                            validation={
                                "accept": "image/*",
                                "maxSize": 5242880,
                                "maxFiles": 5
                            }
                        ).dict()
                    ]
                )
            elif next_step == "confirmation":
                operation_name = "crear" if self.operation == "CREATE" else "editar" if self.operation == "EDIT" else "eliminar"
                message = f"¿Desea {operation_name} el tipo de habitación con los siguientes datos?\n\n"
                
                if self.operation != "DELETE":
                    message += f"""Nombre: {self.form_data.get('name', '')}
Descripción: {self.form_data.get('description', '')}
Capacidad: {self.form_data.get('capacity', '')} personas
Precio: ${self.form_data.get('price', '')} por noche
Comodidades: {', '.join(self.form_data.get('amenities', []))}
Imágenes: {'Sí' if self.form_data.get('images') else 'No'}"""
                else:
                    room_types = await self._get_room_types()
                    room_type = next((r for r in room_types if str(r["id"]) == self.form_data["select"]), None)
                    if room_type:
                        message += f"Tipo de Habitación: {room_type['hotel_name']} - {room_type['name']}"
                
                return AdminChatResponse(
                    message=message,
                    components=[self.get_confirmation_component("room_type", f"¿{operation_name.capitalize()} tipo de habitación?")]
                )
                
        return AdminChatResponse(
            message="Ha ocurrido un error en el proceso. Por favor, intente nuevamente."
        )
        
    async def save_data(self) -> tuple[bool, str]:
        """Guarda los datos del formulario"""
        try:
            if self.operation == "CREATE":
                room_type_data = {
                    "hotel_id": int(self.form_data["hotel"]),
                    "name": self.form_data["name"],
                    "description": self.form_data["description"],
                    "capacity": int(self.form_data["capacity"]),
                    "price_per_night": float(self.form_data["price"]),
                    "amenities": self.form_data.get("amenities", []),
                    "images": self.form_data.get("images", [])
                }
                
                response = self.supabase.table("room_types").insert(room_type_data).execute()
                return True, "✅ Tipo de habitación creado exitosamente. ¿En qué más puedo ayudarle?"
                
            elif self.operation == "EDIT":
                room_type_data = {
                    "name": self.form_data["name"],
                    "description": self.form_data["description"],
                    "capacity": int(self.form_data["capacity"]),
                    "price_per_night": float(self.form_data["price"]),
                    "amenities": self.form_data.get("amenities", []),
                    "images": self.form_data.get("images", [])
                }
                
                response = self.supabase.table("room_types").update(room_type_data).eq("id", int(self.form_data["select"])).execute()
                return True, "✅ Tipo de habitación actualizado exitosamente. ¿En qué más puedo ayudarle?"
                
            elif self.operation == "DELETE":
                response = self.supabase.table("room_types").delete().eq("id", int(self.form_data["select"])).execute()
                return True, "✅ Tipo de habitación eliminado exitosamente. ¿En qué más puedo ayudarle?"
                
        except Exception as e:
            print(f"Error al guardar tipo de habitación: {str(e)}")
            return False, "❌ Ha ocurrido un error al procesar la operación. Por favor, intente nuevamente."
            
    async def _get_hotels(self) -> List[Dict]:
        """Obtiene la lista de hoteles disponibles"""
        try:
            response = self.supabase.table("hotels").select("id, name").eq("agency_id", self.agency_id).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error al obtener hoteles: {str(e)}")
            return []
            
    async def _get_room_types(self) -> List[Dict]:
        """Obtiene la lista de tipos de habitación disponibles"""
        try:
            query = """
                SELECT rt.id, rt.name, h.name as hotel_name
                FROM room_types rt
                JOIN hotels h ON rt.hotel_id = h.id
                WHERE h.agency_id = ?
            """
            response = self.supabase.table("room_types").select("id, name, hotel_id").execute()
            if not response.data:
                return []
                
            # Obtener nombres de hoteles
            hotel_ids = list(set(rt["hotel_id"] for rt in response.data))
            hotels_response = self.supabase.table("hotels").select("id, name").in_("id", hotel_ids).execute()
            hotels = {h["id"]: h["name"] for h in hotels_response.data} if hotels_response.data else {}
            
            # Combinar datos
            return [{
                "id": rt["id"],
                "name": rt["name"],
                "hotel_name": hotels.get(rt["hotel_id"], "Hotel Desconocido")
            } for rt in response.data]
        except Exception as e:
            print(f"Error al obtener tipos de habitación: {str(e)}")
            return []
