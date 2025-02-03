import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class TextFormatter:
    """Clase para mejorar el formateo y estructura de las respuestas del chatbot"""
    
    def __init__(self):
        # Nombres propios y términos especiales que siempre deben ser formateados
        self.special_terms = {
            'parque_tematico': 'Parque Temático Los Quimbayas',
            'restaurante': 'Restaurante Ancestral',
            'piscina': 'Piscina Caverna',
            'zona_camping': 'Zona de Camping Los Ancestros'
        }
        
        # Patrones de markdown para diferentes tipos de contenido
        self.markdown_patterns = {
            'nombres_propios': '**{}**',
            'lugares': '*{}*',
            'precios': '`{}`',
            'horarios': '`{}`',
            'enlaces': '[{}]({})',
            'listas': '- {}',
            'notas': '> {}',
            'secciones': '## {}',
            'subsecciones': '### {}'
        }
        
        # Patrones para identificar tipos de contenido
        self.content_patterns = {
            'lista_numerada': r'^\d+\.\s',
            'lista_items': r'(?m)^[-•]\s',
            'precio': r'\$[\d,]+(?:\.\d{2})?',
            'horario': r'\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)',
            'habitacion': r'(?i)(?:habitación|habitacion|cabaña|cabana|casa)\s+[\w\s]+',
        }

    def format_response(self, text: str, context: Dict[str, Any] = None) -> str:
        """
        Aplica todas las mejoras de formato al texto
        
        Args:
            text: Texto a formatear
            context: Contexto adicional para el formateo
            
        Returns:
            str: Texto formateado con markdown y mejor estructura
        """
        try:
            # Dividir el texto en secciones si contiene múltiples párrafos
            paragraphs = text.split('\n\n')
            formatted_paragraphs = []
            
            for i, paragraph in enumerate(paragraphs):
                formatted_text = paragraph.strip()
                
                # Detectar si es una lista numerada o con viñetas
                if re.match(self.content_patterns['lista_numerada'], formatted_text):
                    # Convertir lista numerada a formato markdown
                    lines = formatted_text.split('\n')
                    formatted_text = '\n\n### Opciones Disponibles\n\n' + '\n'.join(f"{line}" for line in lines)
                
                # Formatear elementos específicos
                formatted_text = self._format_proper_names(formatted_text)
                formatted_text = self._format_prices_and_times(formatted_text)
                formatted_text = self._format_rooms(formatted_text)
                formatted_text = self._improve_punctuation(formatted_text)
                
                # Agregar espaciado y separadores para mejor legibilidad
                if i > 0 and not formatted_text.startswith('#'):
                    formatted_text = '\n\n---\n\n' + formatted_text
                
                formatted_paragraphs.append(formatted_text)
            
            # Unir los párrafos formateados
            result = '\n\n'.join(formatted_paragraphs)
            
            # Aplicar formato adicional basado en el contexto
            if context:
                result = self._apply_context_formatting(result, context)
            
            return result.strip()
            
        except Exception as e:
            logger.error(f"Error al formatear respuesta: {str(e)}")
            return text

    def _format_rooms(self, text: str) -> str:
        """Formatea nombres de habitaciones con markdown"""
        def replace_room(match):
            room = match.group(0)
            return f"**{room}**"
            
        return re.sub(self.content_patterns['habitacion'], replace_room, text)

    def _format_proper_names(self, text: str) -> str:
        """Formatea nombres propios y términos especiales"""
        formatted_text = text
        for term, replacement in self.special_terms.items():
            pattern = r'\b' + re.escape(term) + r'\b'
            formatted_text = re.sub(pattern, f"**{replacement}**", formatted_text, flags=re.IGNORECASE)
        return formatted_text

    def _format_prices_and_times(self, text: str) -> str:
        """Formatea precios y horarios con markdown"""
        # Formatear precios
        formatted_text = re.sub(
            self.content_patterns['precio'],
            lambda m: f"`{m.group()}`",
            text
        )
        
        # Formatear horarios
        formatted_text = re.sub(
            self.content_patterns['horario'],
            lambda m: f"`{m.group()}`",
            formatted_text
        )
        
        return formatted_text

    def _improve_punctuation(self, text: str) -> str:
        """Mejora la puntuación y estructura del texto"""
        # Asegurar espacio después de puntos
        text = re.sub(r'\.(?=[A-ZÁÉÍÓÚÑa-záéíóúñ])', '. ', text)
        
        # Asegurar espacio después de comas
        text = re.sub(r',(?=[A-ZÁÉÍÓÚÑa-záéíóúñ])', ', ', text)
        
        # Eliminar espacios múltiples
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def _apply_context_formatting(self, text: str, context: Dict[str, Any]) -> str:
        """Aplica formato adicional basado en el contexto"""
        formatted_text = text
        
        # Aplicar formato a términos especiales del contexto
        if 'special_terms' in context:
            for term in context['special_terms']:
                formatted_text = re.sub(
                    r'\b' + re.escape(term) + r'\b',
                    f"**{term}**",
                    formatted_text,
                    flags=re.IGNORECASE
                )
        
        # Agregar notas o advertencias si existen en el contexto
        if 'notes' in context:
            formatted_text += '\n\n> ' + context['notes']
            
        return formatted_text
