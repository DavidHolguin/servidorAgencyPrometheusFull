from typing import List, Dict, Any, Optional
import logging
from app.core.supabase_client import get_client

logger = logging.getLogger(__name__)

class GalleryManager:
    """Gestor de galerías e imágenes"""
    
    def __init__(self):
        self.supabase = get_client()
        self._galleries: Dict[str, Any] = {}
        self._gallery_keywords: Dict[str, List[str]] = {}
        
    async def initialize(self):
        """Carga inicial de todas las galerías y sus palabras clave"""
        try:
            # Cargar todas las galerías con sus imágenes y relaciones
            response = self.supabase.table('image_galleries')\
                .select(
                    '*,' 
                    'gallery_images(*),'  # Cargar todas las imágenes
                    'asset_galleries(asset_type,asset_id)'  # Cargar relaciones con assets
                )\
                .order('created_at', desc=True)\
                .execute()
                
            if response.data:
                for gallery in response.data:
                    gallery_id = gallery['id']
                    self._galleries[gallery_id] = gallery
                    
                    # Indexar palabras clave para búsqueda rápida
                    all_keywords = set()
                    
                    # Agregar keywords de la galería
                    if gallery_keywords := gallery.get('keywords', []):
                        all_keywords.update(gallery_keywords)
                    
                    # Agregar nombre y descripción como keywords
                    if name := gallery.get('name'):
                        all_keywords.add(name.lower())
                    if description := gallery.get('description'):
                        all_keywords.add(description.lower())
                    
                    # Agregar keywords de las imágenes
                    for image in gallery.get('gallery_images', []):
                        if image_keywords := image.get('keywords', []):
                            all_keywords.update(image_keywords)
                        if image_name := image.get('name'):
                            all_keywords.add(image_name.lower())
                        if image_desc := image.get('description'):
                            all_keywords.add(image_desc.lower())
                    
                    # Indexar todas las keywords encontradas
                    for keyword in all_keywords:
                        if keyword not in self._gallery_keywords:
                            self._gallery_keywords[keyword] = []
                        self._gallery_keywords[keyword].append(gallery_id)
                        
            logger.info(f"Galerías cargadas: {len(self._galleries)}")
            logger.info(f"Palabras clave indexadas: {len(self._gallery_keywords)}")
            
        except Exception as e:
            logger.error(f"Error cargando galerías: {str(e)}")
            raise
            
    def _calculate_keyword_match_score(self, search_terms: List[str], gallery: Dict[str, Any]) -> float:
        """
        Calcula un puntaje de coincidencia entre términos de búsqueda y una galería
        
        Args:
            search_terms: Lista de términos de búsqueda
            gallery: Datos de la galería
            
        Returns:
            float: Puntaje de coincidencia (0-1)
        """
        if not search_terms:
            return 0.0
            
        matches = 0
        total_checks = 0
        search_terms = [term.lower() for term in search_terms]
        
        # Verificar coincidencias en keywords de la galería
        gallery_keywords = gallery.get('keywords', [])
        if gallery_keywords:
            for term in search_terms:
                if any(term in keyword.lower() for keyword in gallery_keywords):
                    matches += 1
            total_checks += 1
        
        # Verificar coincidencias en nombre y descripción
        if name := gallery.get('name', '').lower():
            if any(term in name for term in search_terms):
                matches += 2  # Mayor peso para coincidencias en el nombre
            total_checks += 2
            
        if description := gallery.get('description', '').lower():
            if any(term in description for term in search_terms):
                matches += 1
            total_checks += 1
        
        # Verificar coincidencias en imágenes
        images = gallery.get('gallery_images', [])
        if images:
            image_matches = 0
            for image in images:
                image_keywords = image.get('keywords', [])
                image_name = image.get('name', '').lower()
                image_desc = image.get('description', '').lower() if image.get('description') else ''
                
                if any(term in keyword.lower() for term in search_terms for keyword in image_keywords):
                    image_matches += 1
                if any(term in image_name for term in search_terms):
                    image_matches += 1
                if any(term in image_desc for term in search_terms):
                    image_matches += 1
            
            if image_matches > 0:
                matches += 1
            total_checks += 1
        
        # Si no hay elementos para verificar, retornar 0
        if total_checks == 0:
            return 0.0
            
        return matches / total_checks
        
    def find_relevant_galleries(self, search_terms: List[str], min_score: float = 0.1) -> List[Dict[str, Any]]:
        """
        Encuentra galerías relevantes basadas en términos de búsqueda
        
        Args:
            search_terms: Lista de términos de búsqueda
            min_score: Puntaje mínimo de coincidencia (0-1)
            
        Returns:
            List[Dict]: Lista de galerías relevantes ordenadas por puntaje
        """
        # Filtrar términos nulos y vacíos
        filtered_terms = [term.lower() for term in search_terms if term and isinstance(term, str)]
        
        # Si no hay términos válidos, devolver todas las galerías
        if not filtered_terms:
            return list(self._galleries.values())
            
        relevant_galleries = []
        
        for gallery_id, gallery in self._galleries.items():
            score = self._calculate_keyword_match_score(filtered_terms, gallery)
            
            if score >= min_score:
                relevant_galleries.append({
                    'gallery': gallery,
                    'score': score
                })
                
        # Ordenar por puntaje descendente
        relevant_galleries.sort(key=lambda x: x['score'], reverse=True)
        return [item['gallery'] for item in relevant_galleries]
        
    def extract_search_terms(self, message: str) -> List[str]:
        """
        Extrae términos de búsqueda de un mensaje
        
        Args:
            message: Mensaje del usuario
            
        Returns:
            List[str]: Lista de términos de búsqueda
        """
        if not message or not isinstance(message, str):
            return []
            
        # Palabras clave que indican que el usuario quiere ver imágenes
        image_indicators = [
            'foto', 'fotos', 'imagen', 'imágenes', 'imagenes', 
            'muestra', 'mostrar', 'ver', 'enseña', 'enseñar'
        ]
        
        # Convertir mensaje a minúsculas y dividir en palabras
        words = message.lower().split()
        
        # Si no hay indicadores de imágenes, retornar lista vacía
        if not any(indicator in words for indicator in image_indicators):
            return []
        
        # Extraer términos relevantes (sustantivos y adjetivos)
        # Por ahora simplemente tomamos todas las palabras que no son indicadores
        search_terms = []
        
        # Palabras a ignorar (artículos, preposiciones, etc.)
        ignore_words = {
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
            'de', 'del', 'en', 'por', 'para', 'con', 'sin',
            'y', 'o', 'pero', 'mas', 'más',
            'que', 'quien', 'quién', 'cual', 'cuál',
            'este', 'esta', 'estos', 'estas',
            'ese', 'esa', 'esos', 'esas',
            'aquel', 'aquella', 'aquellos', 'aquellas'
        }
        
        # Agregar palabras que no son indicadores ni palabras a ignorar
        for word in words:
            if (word not in image_indicators and 
                word not in ignore_words and 
                len(word) > 2):  # Ignorar palabras muy cortas
                search_terms.append(word)
        
        return search_terms

    def format_gallery_response(self, galleries: List[Dict[str, Any]], show_all_images: bool = False) -> Dict[str, Any]:
        """
        Formatea la respuesta con las galerías encontradas
        
        Args:
            galleries: Lista de galerías a mostrar
            show_all_images: Si es True, muestra todas las imágenes. Si es False, muestra solo las primeras 3
            
        Returns:
            Dict[str, Any]: Objeto con las galerías e imágenes encontradas
        """
        if not galleries:
            return {
                "galleries": [],
                "total_images": 0,
                "has_more": False
            }
            
        formatted_galleries = []
        total_images = 0
        has_more = False
        
        for gallery in galleries:
            images = gallery.get('gallery_images', [])
            if not images:
                continue
                
            # Ordenar imágenes por posición
            images.sort(key=lambda x: x.get('position', 0))
            
            # Limitar número de imágenes si es necesario
            displayed_images = images if show_all_images else images[:3]
            has_more = has_more or (not show_all_images and len(images) > 3)
            
            formatted_images = []
            for image in displayed_images:
                if url := image.get('url'):
                    formatted_images.append({
                        "url": url,
                        "name": image.get('name', ''),
                        "description": image.get('description', ''),
                        "metadata": image.get('metadata', {})
                    })
            
            if formatted_images:
                formatted_galleries.append({
                    "id": gallery['id'],
                    "name": gallery['name'],
                    "description": gallery.get('description', ''),
                    "images": formatted_images,
                    "total_images": len(images)
                })
                total_images += len(formatted_images)
        
        return {
            "galleries": formatted_galleries,
            "total_images": total_images,
            "has_more": has_more
        }
