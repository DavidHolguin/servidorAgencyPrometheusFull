from typing import Optional
from app.core.admin.base.base_manager import BaseAssetManager
from app.core.admin.managers.chatbot_manager import ChatbotManager
from app.core.admin.managers.hotel_manager import HotelManager
from app.core.admin.managers.room_manager import RoomTypeManager
from app.core.admin.managers.reservation_manager import ReservationManager
from app.core.admin.managers.lead_manager import LeadManager

class ManagerFactory:
    """Fábrica para crear managers de diferentes tipos de activos"""
    
    def create_manager(self, asset_type: str, agency_id: str) -> Optional[BaseAssetManager]:
        """
        Crea un manager basado en el tipo de activo
        
        Args:
            asset_type: Tipo de activo ('chatbot', 'hotel', etc.)
            agency_id: ID de la agencia
            
        Returns:
            Manager apropiado o None si el tipo no es válido
        """
        managers = {
            "chatbot": ChatbotManager,
            "hotel": HotelManager,
            "room_type": RoomTypeManager,
            "reservation": ReservationManager,
            "lead": LeadManager
        }
        
        manager_class = managers.get(asset_type)
        if manager_class:
            return manager_class(agency_id)
            
        return None
