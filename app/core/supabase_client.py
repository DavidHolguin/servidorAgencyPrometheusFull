import os
from supabase import create_client, Client
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Variables globales
_supabase_client: Optional[Client] = None

def initialize_supabase() -> None:
    """Inicializa el cliente de Supabase"""
    global _supabase_client
    
    try:
        logger.info("Getting Supabase client...")
        
        # Obtener credenciales
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")  # Usamos la clave anon por defecto
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY environment variables are required")
        
        logger.info("Initializing Supabase client...")
        logger.info(f"Supabase URL: {supabase_url}")
        logger.info(f"Supabase Key length: {len(supabase_key)}")
        
        # Crear cliente
        _supabase_client = create_client(supabase_url, supabase_key)
        
        # Probar conexión
        response = _supabase_client.table('chatbots').select('id').limit(1).execute()
        record_count = len(response.data) if response.data else 0
        logger.info(f"Test query successful, found {record_count} records")
        
        logger.info(f"Supabase client initialized: {_supabase_client is not None}")
        
    except Exception as e:
        logger.error(f"Error initializing Supabase client: {str(e)}")
        raise

def get_client() -> Client:
    """Obtiene el cliente de Supabase inicializado"""
    if not _supabase_client:
        raise RuntimeError("Supabase client not initialized. Call initialize_supabase() first.")
    return _supabase_client
