# app/config/settings.py
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import os

class Settings(BaseSettings):
    # Configuración general de la aplicación
    app_name: str = "Travel Chatbot API"
    port: int = int(os.getenv("PORT", "8000"))
    base_url: str = os.getenv("BASE_URL", "http://localhost:8000")
    environment: str = os.getenv("ENVIRONMENT", "development")

    # OpenAI
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY", "")  # Hacer openai_api_key opcional

    # Supabase
    supabase_url: str = os.getenv("SUPABASE_URL", "https://eawutspxunldlkfesgik.supabase.co")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    supabase_admin_email: Optional[str] = os.getenv("SUPABASE_ADMIN_EMAIL", "admin@agency.com")
    supabase_admin_password: Optional[str] = os.getenv("SUPABASE_ADMIN_PASSWORD", "admin123")

    # WhatsApp Business API
    whatsapp_api_token: Optional[str] = os.getenv("WHATSAPP_API_TOKEN", "")  # Hacer whatsapp_api_token opcional
    whatsapp_webhook_verify_token: str = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "your-verify-token")  # Token para verificar webhooks
    whatsapp_business_phone_number: Optional[str] = os.getenv("WHATSAPP_BUSINESS_PHONE_NUMBER", "")  # Hacer whatsapp_business_phone_number opcional
    whatsapp_business_account_id: Optional[str] = None  # ID de la cuenta de WhatsApp Business
    whatsapp_api_version: str = "v17.0"  # Versión de la API de WhatsApp
    whatsapp_phone_number_id: Optional[str] = None  # ID del número de teléfono de WhatsApp

    # Meta API (Facebook)
    meta_app_id: Optional[str] = None
    meta_app_secret: Optional[str] = None

    # Redis (opcional, para caché)
    redis_url: Optional[str] = None
    redis_password: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
        validate_default = True

    def validate_required_settings(self):
        """Validar configuraciones requeridas basadas en el entorno"""
        if self.environment == "production":
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY es requerido en producción")
            if not self.supabase_url or not self.supabase_anon_key or not self.supabase_service_key:
                raise ValueError("SUPABASE_URL, SUPABASE_ANON_KEY y SUPABASE_SERVICE_KEY son requeridos en producción")
            if not self.whatsapp_api_token:
                raise ValueError("WHATSAPP_API_TOKEN es requerido en producción")

@lru_cache()
def get_settings() -> Settings:
    try:
        settings = Settings()
        if os.getenv("ENVIRONMENT") == "production":
            settings.validate_required_settings()
        return settings
    except Exception as e:
        print(f"Error loading settings: {e}")
        # En desarrollo, permitir valores por defecto
        if os.getenv("ENVIRONMENT") != "production":
            return Settings(_env_file=None)
        raise  # En producción, propagar el error
