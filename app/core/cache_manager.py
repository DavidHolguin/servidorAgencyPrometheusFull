from typing import Dict, List, Any
import logging
from datetime import datetime
from .supabase_client import get_client

logger = logging.getLogger(__name__)

class CacheManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if not self.initialized:
            self.supabase = get_client()
            self.cache = {
                'image_galleries': [],
                'gallery_images': {},  # Diccionario con gallery_id como clave
                'rooms': [],
                'room_types': [],
                'chatbots': [],
                'reservations': []
            }
            self.initialized = True
    
    async def initialize_cache(self):
        """Carga todos los datos necesarios en el caché"""
        try:
            # Cargar galerías de imágenes
            galleries_response = self.supabase.table('image_galleries').select('*').execute()
            self.cache['image_galleries'] = galleries_response.data

            # Cargar imágenes para cada galería
            for gallery in self.cache['image_galleries']:
                images_response = self.supabase.table('gallery_images')\
                    .select('*')\
                    .eq('gallery_id', gallery['id'])\
                    .execute()
                self.cache['gallery_images'][gallery['id']] = images_response.data

            # Cargar tipos de habitaciones
            room_types_response = self.supabase.table('room_types').select('*').execute()
            self.cache['room_types'] = room_types_response.data

            # Cargar habitaciones
            rooms_response = self.supabase.table('rooms').select('*').execute()
            self.cache['rooms'] = rooms_response.data

            # Cargar chatbots
            chatbots_response = self.supabase.table('chatbots').select('*').execute()
            self.cache['chatbots'] = chatbots_response.data

            # Cargar reservas activas
            reservations_response = self.supabase.table('reservations')\
                .select('*')\
                .eq('status', 'active')\
                .execute()
            self.cache['reservations'] = reservations_response.data

            logger.info("Cache initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing cache: {str(e)}")
            return False

    def get_images_for_entity(self, entity_name: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Busca imágenes relacionadas con una entidad específica usando metadata
        
        Args:
            entity_name: Nombre de la entidad (ej: 'casa_arbol', 'habitacion_suite', etc)
            metadata: Diccionario con metadata adicional para filtrar
        
        Returns:
            Lista de imágenes que coinciden con los criterios
        """
        matching_images = []
        
        # Buscar en todas las galerías
        for gallery in self.cache['image_galleries']:
            gallery_images = self.cache['gallery_images'].get(gallery['id'], [])
            
            for image in gallery_images:
                image_metadata = image.get('metadata', {})
                
                # Verificar si la imagen está relacionada con la entidad
                if entity_name.lower() in image_metadata.get('entity_name', '').lower():
                    # Si hay metadata adicional, verificar que coincida
                    if metadata:
                        matches_metadata = all(
                            str(image_metadata.get(key, '')).lower() == str(value).lower()
                            for key, value in metadata.items()
                        )
                        if matches_metadata:
                            matching_images.append(image)
                    else:
                        matching_images.append(image)
        
        return matching_images

    def get_entity_data(self, entity_type: str, entity_id: str = None) -> Dict[str, Any]:
        """
        Obtiene datos de una entidad específica del caché
        
        Args:
            entity_type: Tipo de entidad ('rooms', 'room_types', etc)
            entity_id: ID opcional de la entidad específica
        
        Returns:
            Datos de la entidad o lista de entidades
        """
        if entity_type not in self.cache:
            return None
            
        if entity_id:
            return next(
                (item for item in self.cache[entity_type] if item['id'] == entity_id),
                None
            )
        
        return self.cache[entity_type]

    async def get_cached_response(self, message: str) -> str:
        """Obtiene una respuesta cacheada para un mensaje"""
        try:
            # En lugar de usar una tabla específica, usamos el caché en memoria
            message_hash = hash(message)
            if message_hash in self.cache.get('responses', {}):
                return self.cache['responses'][message_hash]['response']
            return None
        except Exception as e:
            logger.error(f"Error getting cached response: {str(e)}")
            return None
            
    async def cache_response(self, message: str, response: str):
        """Guarda una respuesta en el caché"""
        try:
            # Guardar en caché en memoria
            message_hash = hash(message)
            if 'responses' not in self.cache:
                self.cache['responses'] = {}
            
            self.cache['responses'][message_hash] = {
                'message': message,
                'response': response,
                'created_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error caching response: {str(e)}")
