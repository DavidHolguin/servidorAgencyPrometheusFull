from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Dict

from app.api.v1.chat import router as chat_router
from app.core.supabase_client import initialize_supabase
from app.core.chatbot import ChatbotManager
from app.core.state import active_chatbots

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        # Inicializar cliente de Supabase
        initialize_supabase()
        logger.info("Supabase client initialized successfully")
        
        yield
        
    finally:
        # Shutdown
        try:
            # Limpiar todos los chatbots activos
            cleanup_tasks = [
                chatbot.cleanup() 
                for chatbot in active_chatbots.values()
            ]
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            active_chatbots.clear()
            
            logger.info("Application shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")

app = FastAPI(
    title="Travel Chatbot API",
    description="API para gestionar chatbots de viajes con integración a OpenAI y Supabase",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Soporte Travel Chatbot",
        "email": "soporte@travelchatbot.com",
    },
    license_info={
        "name": "Privado",
    },
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tags para la documentación
tags_metadata = [
    {
        "name": "chatbot",
        "description": "Operaciones con el chatbot: envío y recepción de mensajes",
    },
    {
        "name": "webhooks",
        "description": "Endpoints para webhooks de WhatsApp, Messenger, etc.",
    },
    {
        "name": "reservas",
        "description": "Gestión de reservas y disponibilidad",
    },
]

@app.get("/", tags=["general"])
async def root():
    """
    Endpoint de bienvenida que verifica que el servidor está funcionando.
    """
    return {
        "message": "Bienvenido a Travel Chatbot API",
        "version": "1.0.0",
        "status": "online",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Ruta de prueba para verificar conexión a Supabase
@app.get("/test-supabase")
async def test_supabase():
    from app.core.supabase import supabase, get_supabase_client
    from app.config.settings import get_settings
    
    settings = get_settings()
    print(f"SUPABASE_URL: {settings.supabase_url}")
    print(f"SUPABASE_KEY length: {len(settings.supabase_key) if settings.supabase_key else 0}")
    
    client = get_supabase_client()
    if client is None:
        return {"error": "Supabase client is None"}
        
    try:
        response = client.table('chatbots').select('*').limit(1).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        return {"error": str(e)}

# Incluir routers
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])

# Importar routers
from app.api.v1 import reservas, webhooks, admin_chat

# Incluir routers con sus prefijos
app.include_router(reservas.router, prefix="/api/v1", tags=["reservas"])
app.include_router(webhooks.router, prefix="/api/v1", tags=["webhooks"])
app.include_router(admin_chat.router, prefix="/api/v1", tags=["admin_chat"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
