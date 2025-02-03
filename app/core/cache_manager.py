from typing import Dict, List, Any
import logging
from datetime import datetime, timedelta
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
            # Añadir timestamps de última actualización y tiempos de expiración
            self.last_update = {
                'image_galleries': None,
                'gallery_images': None,
                'rooms': None,
                'room_types': None,
                'chatbots': None,
                'reservations': None
            }
            # Configurar tiempos de expiración por tipo de dato (en segundos)
            self.expiration_times = {
                'image_galleries': 3600,  # 1 hora
                'gallery_images': 3600,  # 1 hora
                'rooms': 300,           # 5 minutos
                'room_types': 1800,     # 30 minutos
                'chatbots': 60,         # 1 minuto (actualización frecuente)
                'reservations': 120     # 2 minutos
            }
            self.initialized = True
    
    def _is_cache_valid(self, cache_type: str) -> bool:
        """
        Verifica si el caché para un tipo específico es válido
        
        Args:
            cache_type: Tipo de caché a verificar
            
        Returns:
            bool: True si el caché es válido, False si necesita actualizarse
        """
        if not self.last_update[cache_type]:
            return False
            
        expiration_time = self.expiration_times[cache_type]
        time_diff = (datetime.now() - self.last_update[cache_type]).total_seconds()
        
        return time_diff < expiration_time
    
    async def refresh_cache(self, cache_type: str = None):
        """
        Actualiza el caché para un tipo específico o todos si no se especifica
        
        Args:
            cache_type: Tipo específico de caché a actualizar (opcional)
        """
        try:
            types_to_refresh = [cache_type] if cache_type else self.cache.keys()
            
            for cache_type in types_to_refresh:
                if cache_type == 'chatbots':
                    # Actualizar chatbots
                    response = self.supabase.table('chatbots').select('*').execute()
                    self.cache['chatbots'] = response.data
                    self.last_update['chatbots'] = datetime.now()
                    
                elif cache_type == 'image_galleries':
                    # Actualizar galerías
                    response = self.supabase.table('image_galleries').select('*').execute()
                    self.cache['image_galleries'] = response.data
                    self.last_update['image_galleries'] = datetime.now()
                    
                    # Actualizar imágenes de galerías
                    for gallery in self.cache['image_galleries']:
                        images_response = self.supabase.table('gallery_images')\
                            .select('*')\
                            .eq('gallery_id', gallery['id'])\
                            .execute()
                        self.cache['gallery_images'][gallery['id']] = images_response.data
                    self.last_update['gallery_images'] = datetime.now()
                    
                elif cache_type == 'rooms':
                    # Actualizar habitaciones
                    response = self.supabase.table('rooms').select('*').execute()
                    self.cache['rooms'] = response.data
                    self.last_update['rooms'] = datetime.now()
                    
                elif cache_type == 'room_types':
                    # Actualizar tipos de habitaciones
                    response = self.supabase.table('room_types').select('*').execute()
                    self.cache['room_types'] = response.data
                    self.last_update['room_types'] = datetime.now()
                    
                elif cache_type == 'reservations':
                    # Actualizar reservas activas
                    response = self.supabase.table('reservations')\
                        .select('*')\
                        .eq('status', 'active')\
                        .execute()
                    self.cache['reservations'] = response.data
                    self.last_update['reservations'] = datetime.now()
                    
            logger.info(f"Cache refreshed successfully for: {types_to_refresh}")
            
        except Exception as e:
            logger.error(f"Error refreshing cache: {str(e)}")
            
    async def get_chatbot_data(self, chatbot_id: str = None) -> Any:
        """
        Obtiene datos de chatbot del caché, actualizando si es necesario
        
        Args:
            chatbot_id: ID opcional del chatbot específico
            
        Returns:
            Datos del chatbot o lista de chatbots
        """
        if not self._is_cache_valid('chatbots'):
            await self.refresh_cache('chatbots')
            
        if chatbot_id:
            return next(
                (bot for bot in self.cache['chatbots'] if bot['id'] == chatbot_id),
                None
            )
        return self.cache['chatbots']

    async def initialize_cache(self):
        """Carga todos los datos necesarios en el caché"""
        try:
            # Cargar galerías de imágenes
            galleries_response = self.supabase.table('image_galleries').select('*').execute()
            self.cache['image_galleries'] = galleries_response.data
            self.last_update['image_galleries'] = datetime.now()

            # Cargar imágenes para cada galería
            for gallery in self.cache['image_galleries']:
                images_response = self.supabase.table('gallery_images')\
                    .select('*')\
                    .eq('gallery_id', gallery['id'])\
                    .execute()
                self.cache['gallery_images'][gallery['id']] = images_response.data
            self.last_update['gallery_images'] = datetime.now()

            # Cargar tipos de habitaciones
            room_types_response = self.supabase.table('room_types').select('*').execute()
            self.cache['room_types'] = room_types_response.data
            self.last_update['room_types'] = datetime.now()

            # Cargar habitaciones
            rooms_response = self.supabase.table('rooms').select('*').execute()
            self.cache['rooms'] = rooms_response.data
            self.last_update['rooms'] = datetime.now()

            # Cargar chatbots
            chatbots_response = self.supabase.table('chatbots').select('*').execute()
            self.cache['chatbots'] = chatbots_response.data
            self.last_update['chatbots'] = datetime.now()

            # Cargar reservas activas
            reservations_response = self.supabase.table('reservations')\
                .select('*')\
                .eq('status', 'active')\
                .execute()
            self.cache['reservations'] = reservations_response.data
            self.last_update['reservations'] = datetime.now()

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
