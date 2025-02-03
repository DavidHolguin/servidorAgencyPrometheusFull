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
            'notas': '> {}'
        }
    
    def _format_proper_names(self, text: str) -> str:
        """Formatea nombres propios y términos especiales"""
        formatted_text = text
        for key, value in self.special_terms.items():
            # Busca el término especial y lo reemplaza con formato markdown
            pattern = re.compile(r'\b' + value + r'\b', re.IGNORECASE)
            formatted_text = pattern.sub(self.markdown_patterns['nombres_propios'].format(value), formatted_text)
        return formatted_text
    
    def _format_prices_and_times(self, text: str) -> str:
        """Formatea precios y horarios con markdown"""
        # Formato para precios (ej: $50.000)
        price_pattern = r'\$\d{1,3}(?:\.\d{3})*(?:,\d{2})?'
        formatted_text = re.sub(
            price_pattern,
            lambda m: self.markdown_patterns['precios'].format(m.group()),
            text
        )
        
        # Formato para horarios (ej: 9:00 AM - 5:00 PM)
        time_pattern = r'\b(?:1[0-2]|0?[1-9])(?::[0-5][0-9])?\s*(?:AM|PM)\s*-\s*(?:1[0-2]|0?[1-9])(?::[0-5][0-9])?\s*(?:AM|PM)\b'
        formatted_text = re.sub(
            time_pattern,
            lambda m: self.markdown_patterns['horarios'].format(m.group()),
            formatted_text
        )
        
        return formatted_text
    
    def _improve_punctuation(self, text: str) -> str:
        """Mejora la puntuación del texto"""
        # Corrige espacios alrededor de signos de puntuación
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        text = re.sub(r'([.,;:!?])(?!\s|$)', r'\1 ', text)
        
        # Asegura que haya un espacio después de comas y puntos
        text = re.sub(r'([.,])([^\s\d])', r'\1 \2', text)
        
        # Corrige múltiples espacios
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _format_lists(self, text: str) -> str:
        """Formatea listas en el texto"""
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Si la línea comienza con un número o un guion, aplicar formato de lista
            if re.match(r'^\s*(?:\d+\.|[-•])\s+', line):
                # Elimina el marcador original y aplica el formato markdown
                clean_line = re.sub(r'^\s*(?:\d+\.|[-•])\s+', '', line)
                formatted_lines.append(self.markdown_patterns['listas'].format(clean_line))
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def format_response(self, text: str, context: Dict[str, Any] = None) -> str:
        """
        Aplica todas las mejoras de formato al texto
        
        Args:
            text: Texto a formatear
            context: Contexto adicional para el formateo
            
        Returns:
            str: Texto formateado con markdown y mejor puntuación
        """
        try:
            # Aplicar mejoras de formato en orden
            formatted_text = text
            formatted_text = self._improve_punctuation(formatted_text)
            formatted_text = self._format_proper_names(formatted_text)
            formatted_text = self._format_prices_and_times(formatted_text)
            formatted_text = self._format_lists(formatted_text)
            
            # Si hay contexto específico, aplicar formatos adicionales
            if context:
                if 'special_terms' in context:
                    for term in context['special_terms']:
                        formatted_text = re.sub(
                            r'\b' + term + r'\b',
                            self.markdown_patterns['nombres_propios'].format(term),
                            formatted_text,
                            flags=re.IGNORECASE
                        )
            
            return formatted_text
            
        except Exception as e:
            logger.error(f"Error al formatear texto: {str(e)}")
            return text  # Devolver texto original si hay error
