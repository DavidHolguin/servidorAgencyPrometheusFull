from typing import List, Dict, Any
import logging
import re
from app.core.gallery_manager import GalleryManager
from app.core.weight_system import WeightSystem
from app.core.text_formatter import TextFormatter
from app.core.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class ResponseEnricher:
    """Clase para enriquecer las respuestas del chatbot con elementos visuales y formateo"""
    
    def __init__(self):
        self.gallery_manager = GalleryManager()
        self.weight_system = WeightSystem()
        self.text_formatter = TextFormatter()
        self.cache_manager = CacheManager()
        
    async def initialize(self):
        """Inicializa el ResponseEnricher cargando datos necesarios"""
        await self.gallery_manager.initialize()
        await self.cache_manager.initialize_cache()

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

    def _generate_image_message(self, search_terms: List[str], gallery_name: str = None) -> str:
        """
        Genera un mensaje contextual para las imágenes basado en los términos de búsqueda
        
        Args:
            search_terms: Términos de búsqueda usados para encontrar las imágenes
            gallery_name: Nombre de la galería encontrada (opcional)
            
        Returns:
            str: Mensaje contextual para las imágenes
        """
        if not search_terms:
            return "¡Aquí tienes algunas fotos! 📸"
            
        # Limpia y procesa los términos de búsqueda
        clean_terms = [term.lower().strip() for term in search_terms if term.strip()]
        
        # Mapeo de términos comunes a frases contextuales
        context_mapping = {
            'piscina': 'de nuestra piscina',
            'restaurante': 'de nuestro restaurante',
            'habitacion': 'de nuestras habitaciones',
            'habitaciones': 'de nuestras habitaciones',
            'camping': 'de nuestra zona de camping',
            'instalacion': 'de nuestras instalaciones',
            'instalaciones': 'de nuestras instalaciones',
            'parque': 'del parque',
            'zonas': 'de nuestras zonas',
            'zona': 'de esta zona'
        }
        
        # Busca coincidencias en el mapeo
        for term in clean_terms:
            for key, phrase in context_mapping.items():
                if key in term:
                    return f"¡Aquí tienes algunas fotos {phrase}! 📸"
        
        # Si hay un nombre de galería, úsalo para contextualizar
        if gallery_name:
            return f"¡Aquí tienes algunas fotos relacionadas con {gallery_name}! 📸"
            
        # Mensaje genérico pero usando los términos de búsqueda
        search_context = ' y '.join(clean_terms)
        return f"¡Aquí tienes algunas fotos relacionadas con {search_context}! 📸"

    async def _get_chatbot_config(self, chatbot_id: str = None) -> Dict[str, Any]:
        """
        Obtiene la configuración actualizada del chatbot
        
        Args:
            chatbot_id: ID del chatbot
            
        Returns:
            Dict con la configuración del chatbot
        """
        return await self.cache_manager.get_chatbot_data(chatbot_id)

    async def enrich_response(
        self,
        llm_response: str,
        search_terms: List[str],
        chatbot_config: Dict[str, Any] = None,
        chatbot_id: str = None
    ) -> Dict[str, Any]:
        try:
            # Si tenemos un chatbot_id, obtener configuración actualizada
            if chatbot_id:
                chatbot_config = await self._get_chatbot_config(chatbot_id)
            
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
            for gallery in galleries:
                gallery_images = []
                
                # Procesar imágenes de la galería - solo incluir URLs
                for image in gallery.get('gallery_images', []):
                    if url := image.get('url'):
                        gallery_images.append({
                            'url': url
                        })
                
                if gallery_images:  # Solo incluir galerías que tengan imágenes
                    enriched_galleries.append({
                        'name': gallery.get('name', ''),
                        'images': gallery_images
                    })
            
            # Si hay galerías, modificar el texto para que sea contextual
            if enriched_galleries:
                gallery_name = enriched_galleries[0].get('name') if enriched_galleries else None
                processed_text = self._generate_image_message(filtered_terms, gallery_name)
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
