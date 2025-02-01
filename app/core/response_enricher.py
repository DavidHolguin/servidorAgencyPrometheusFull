from typing import List, Dict, Any
import logging
import re
from app.core.gallery_manager import GalleryManager

logger = logging.getLogger(__name__)

class ResponseEnricher:
    """Clase para enriquecer las respuestas del chatbot con elementos visuales y formateo"""
    
    def __init__(self):
        self.gallery_manager = GalleryManager()
        
    async def initialize(self):
        """Inicializa el ResponseEnricher cargando datos necesarios"""
        await self.gallery_manager.initialize()
    
    async def enrich_response(
        self,
        llm_response: str,
        search_terms: List[str]
    ) -> Dict[str, Any]:
        """
        Enriquece la respuesta del chatbot con galerías de imágenes relevantes
        
        Args:
            llm_response: Texto de respuesta del chatbot
            search_terms: Términos de búsqueda para encontrar galerías relevantes
            
        Returns:
            Dict con la respuesta enriquecida y las galerías encontradas
        """
        try:
            # Inicializar respuesta
            enriched_response = {
                'text': llm_response,
                'galleries': []
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
            
            # Preparar las galerías con sus imágenes
            enriched_galleries = []
            for gallery in galleries:
                gallery_images = []
                
                # Procesar imágenes de la galería
                for image in gallery.get('gallery_images', []):
                    if url := image.get('url'):
                        gallery_images.append({
                            'url': url,
                            'name': image.get('name', ''),
                            'description': image.get('description', '')
                        })
                
                if gallery_images:  # Solo incluir galerías que tengan imágenes
                    enriched_galleries.append({
                        'id': gallery.get('id'),
                        'name': gallery.get('name', ''),
                        'description': gallery.get('description', ''),
                        'images': gallery_images
                    })
            
            enriched_response['galleries'] = enriched_galleries
            return enriched_response
            
        except Exception as e:
            logger.error(f"Error enriqueciendo respuesta: {str(e)}")
            # En caso de error, devolver solo el texto original
            return {
                'text': llm_response,
                'galleries': []
            }
