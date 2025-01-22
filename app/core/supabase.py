# app/core/supabase.py
from supabase import create_client, Client
from app.config.settings import get_settings
from functools import lru_cache
import os
from postgrest import APIResponse
from typing import Optional

@lru_cache()
def get_supabase_client() -> Optional[Client]:
    """Get a cached Supabase client instance"""
    settings = get_settings()
    
    print("Initializing Supabase client...")
    print(f"Supabase URL: {settings.supabase_url}")
    print(f"Supabase Key length: {len(settings.supabase_key) if settings.supabase_key else 0}")
    
    # Validate Supabase credentials
    if not settings.supabase_url or not settings.supabase_key:
        print("Error: Missing Supabase credentials")
        if os.getenv("ENVIRONMENT") == "production":
            raise ValueError("Supabase credentials are required in production")
        print("Warning: Running without Supabase in development mode")
        return None
    
    try:
        client = create_client(settings.supabase_url, settings.supabase_key)
        print("Supabase client initialized successfully")
        
        # Test the connection
        try:
            response = client.table('chatbots').select("*").limit(1).execute()
            if isinstance(response, dict):
                data = response.get('data', [])
            elif isinstance(response, APIResponse):
                data = response.data
            else:
                data = []
            print(f"Test query successful, found {len(data)} records")
            return client
        except Exception as e:
            print(f"Test query failed: {str(e)}")
            if os.getenv("ENVIRONMENT") == "production":
                raise
            return None
            
    except Exception as e:
        print(f"Failed to initialize Supabase client: {str(e)}")
        if os.getenv("ENVIRONMENT") == "production":
            raise Exception(f"Failed to initialize Supabase client: {str(e)}")
        return None

# Inicializar el cliente
print("Getting Supabase client...")
supabase = get_supabase_client()
print(f"Supabase client initialized: {supabase is not None}")