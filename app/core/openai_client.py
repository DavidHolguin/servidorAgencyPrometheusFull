# app/core/openai_client.py
from openai import OpenAI
from app.config.settings import get_settings
import logging

settings = get_settings()

try:
    client = OpenAI(api_key=settings.openai_api_key)
    # Verificar que la clave API es válida
    models = client.models.list()
    print("OpenAI client initialized successfully")
except Exception as e:
    print(f"Error initializing OpenAI client: {str(e)}")
    raise e