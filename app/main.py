from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime

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
    }
)

# Configuración de CORS
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

# Importar routers
from app.api.v1.chat import router as chat_router
from app.api.v1.webhooks import router as webhook_router
from app.api.v1.reservas import router as reservas_router

# Incluir routers con sus prefijos
app.include_router(chat_router, prefix="/api/v1/chat", tags=["chatbot"])
app.include_router(webhook_router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(reservas_router, prefix="/api/v1/reservas", tags=["reservas"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
