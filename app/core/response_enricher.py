from typing import List, Dict, Any
import logging
import re
from app.core.gallery_manager import GalleryManager
from app.core.weight_system import WeightSystem
from app.core.text_formatter import TextFormatter

logger = logging.getLogger(__name__)

class ResponseEnricher:
    """Clase para enriquecer las respuestas del chatbot con elementos visuales y formateo"""
    
    def __init__(self):
        self.gallery_manager = GalleryManager()
        self.weight_system = WeightSystem()
        self.text_formatter = TextFormatter()
        
    async def initialize(self):
        """Inicializa el ResponseEnricher cargando datos necesarios"""
        await self.gallery_manager.initialize()
    
    def _clean_image_references(self, text: str) -> str:
        """
        Elimina referencias a imágenes del texto
        
        Args:
            text: Texto a limpiar
            
        Returns:
            Texto sin referencias a imágenes
        """
        # Elimina referencias del tipo [Imagen de X]
        text = re.sub(r'\[Imagen[^]]*\]', '', text)
        # Elimina referencias del tipo (Imagen de X)
        text = re.sub(r'\(Imagen[^)]*\)', '', text)
        # Elimina líneas vacías múltiples
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()
    
    def _process_emojis(self, text: str, chatbot_config: Dict[str, Any]) -> str:
        """
        Procesa los emojis según la configuración del chatbot
        
        Args:
            text: Texto a procesar
            chatbot_config: Configuración del chatbot
            
        Returns:
            Texto con emojis procesados según configuración
        """
        if not chatbot_config.get('personality', {}).get('use_emojis', True):
            # Si use_emojis es False, elimina todos los emojis
            return re.sub(r'[\U0001F300-\U0001F9FF]', '', text)
        return text

    async def enrich_response(
        self,
        llm_response: str,
        search_terms: List[str],
        chatbot_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Enriquece la respuesta del chatbot con galerías de imágenes relevantes y aplica sistema de pesos
        
        Args:
            llm_response: Texto de respuesta del chatbot
            search_terms: Términos de búsqueda para encontrar galerías relevantes
            chatbot_config: Configuración del chatbot
            
        Returns:
            Dict con la respuesta enriquecida, galerías y metadatos de pesos
        """
        try:
            # Procesar el texto
            processed_text = self._clean_image_references(llm_response)
            if chatbot_config:
                processed_text = self._process_emojis(processed_text, chatbot_config)
                
            # Aplicar formato mejorado al texto
            formatted_text = self.text_formatter.format_response(
                processed_text,
                context=chatbot_config
            )
            
            # Aplicar sistema de pesos
            weighted_response = self.weight_system.apply_weights_to_response(
                formatted_text, 
                chatbot_config or {}
            )
            
            # Inicializar respuesta
            enriched_response = {
                'text': weighted_response['text'],
                'galleries': [],
                'weights': weighted_response['weights_applied'],
                'context_relevance': weighted_response['context_relevance'],
                'metadata': weighted_response['metadata']
            }
            
            # Validar términos de búsqueda
            if not search_terms or not isinstance(search_terms, list):
                return enriched_response
                
            # Filtrar términos nulos y vacíos
            filtered_terms = [term for term in search_terms if term and isinstance(term, str)]
            if not filtered_terms:
                return enriched_response
            
            # Buscar galerías relevantes
            galleries = self.gallery_manager.find_relevant_galleries(filtered_terms)
            
            # Preparar las galerías con sus imágenes de forma concisa
            enriched_galleries = []
            
            # Solo usar la primera galería si existe
            if galleries:
                first_gallery = galleries[0]  # Tomar solo la primera galería
                gallery_images = []
                
                # Procesar imágenes de la galería - solo incluir URLs
                for image in first_gallery.get('gallery_images', []):
                    if url := image.get('url'):
                        gallery_images.append({
                            'url': url
                        })
                
                if gallery_images:  # Solo incluir la galería si tiene imágenes
                    enriched_galleries.append({
                        'name': first_gallery.get('name', ''),
                        'images': gallery_images
                    })
            
            # Si hay galerías, modificar el texto para que sea más conciso
            if enriched_galleries:
                processed_text = "¡Aquí tienes algunas fotos de nuestras instalaciones! 📸"
            
            enriched_response['text'] = processed_text
            enriched_response['galleries'] = enriched_galleries
            return enriched_response
            
        except Exception as e:
            logger.error(f"Error enriqueciendo respuesta: {str(e)}")
            # En caso de error, devolver solo el texto original
            return {
                'text': llm_response,
                'galleries': []
            }
