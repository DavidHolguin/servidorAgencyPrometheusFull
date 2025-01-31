from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ResponseEnricher:
    """Clase para enriquecer las respuestas del chatbot con elementos visuales y formateo"""
    
    def format_room_availability(self, rooms: List[Dict], check_in: datetime, check_out: datetime) -> str:
        """Formatea la información de disponibilidad de habitaciones en markdown con imágenes"""
        try:
            if not rooms:
                return "Lo siento, no hay habitaciones disponibles para las fechas seleccionadas."
            
            markdown = []  # Usar lista para concatenación más eficiente
            
            for room in rooms:
                # Agregar imágenes primero
                if room.get('images'):
                    markdown.append("<div class='image-gallery'>\n")
                    for image in room['images']:
                        markdown.append(f"![{image.get('description', room['name'])}]({image['url']})\n")
                    markdown.append("</div>\n\n")
                
                # Información básica
                markdown.append(f"### 🏨 {room['name']}\n\n")
                
                if room.get('description'):
                    markdown.append(f"{room['description']}\n\n")
                
                if room.get('price_per_night'):
                    markdown.append(f"💰 **Precio por noche:** ${room['price_per_night']}\n")
                
                # Características principales
                features = []
                if room.get('max_occupancy'):
                    features.append(f"👥 Capacidad: {room['max_occupancy']} personas")
                if room.get('beds'):
                    features.append(f"🛏️ Camas: {room['beds']}")
                if room.get('bathrooms'):
                    features.append(f"🚿 Baños: {room['bathrooms']}")
                
                if features:
                    markdown.append("\n**Características:**\n")
                    markdown.append("\n".join(f"- {feature}" for feature in features))
                    markdown.append("\n")
                
                # Amenidades
                if room.get('amenities'):
                    markdown.append("\n**✨ Amenidades:**\n")
                    for amenity in room['amenities']:
                        icon = amenity.get('icon', '•')
                        markdown.append(f"- {icon} {amenity['name']}\n")
                
                markdown.append("\n---\n\n")
            
            # Acciones rápidas
            markdown.append("### 🎯 Acciones Rápidas\n\n")
            markdown.append("1. [📅 Reservar Ahora](#booking)\n")
            markdown.append("2. [🔍 Ver Más Detalles](#details)\n")
            markdown.append("3. [📸 Ver Más Fotos](#gallery)\n")
            
            return "".join(markdown)
            
        except Exception as e:
            logger.error(f"Error formatting room availability: {str(e)}")
            return "Error al formatear la información de las habitaciones."
    
    def format_booking_confirmation(self, booking_data: Dict[str, Any]) -> str:
        """Formatea la confirmación de reserva en markdown con QR"""
        try:
            markdown = "### 🎉 ¡Reserva Confirmada!\n\n"
            
            # Detalles principales
            markdown += f"🏨 **Hotel:** {booking_data['hotel_name']}\n"
            markdown += f"🛏️ **Habitación:** {booking_data['room_type']}\n"
            markdown += f"📅 **Check-in:** {booking_data['check_in']}\n"
            markdown += f"📅 **Check-out:** {booking_data['check_out']}\n"
            markdown += f"💰 **Total:** ${booking_data['total_amount']}\n\n"
            
            # Código QR
            if booking_data.get('qr_code'):
                markdown += "### 📱 Código QR para Check-in\n\n"
                markdown += f"![QR Code]({booking_data['qr_code']})\n\n"
            
            # Instrucciones
            markdown += "### ℹ️ Información Importante\n\n"
            markdown += "* Check-in a partir de las 15:00\n"
            markdown += "* Check-out hasta las 12:00\n"
            markdown += "* Presentar identificación oficial\n"
            markdown += "* Mostrar este código QR en recepción\n\n"
            
            return markdown
            
        except Exception as e:
            logger.error(f"Error formatting booking confirmation: {str(e)}")
            return "Error al formatear la confirmación de reserva."
