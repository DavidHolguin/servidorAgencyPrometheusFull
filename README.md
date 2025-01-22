# Travel Chatbot Server

API REST construida con FastAPI para gestionar chatbots de viajes con integración a OpenAI y Supabase.

## Características

- Procesamiento de mensajes con ChatGPT
- Integración con múltiples canales (Web, WhatsApp, Messenger)
- Gestión de reservas y disponibilidad
- Almacenamiento en Supabase
- Documentación automática con Swagger

## Requisitos

- Python 3.9+
- OpenAI API Key
- Supabase Project Credentials

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/yourusername/travel-chatbot-server.git
cd travel-chatbot-server
```

2. Crear y activar entorno virtual:
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
Crear archivo `.env` con:
```env
OPENAI_API_KEY=tu_api_key
SUPABASE_URL=tu_supabase_url
SUPABASE_KEY=tu_supabase_key
```

## Uso

1. Iniciar servidor de desarrollo:
```bash
uvicorn app.main:app --reload
```

2. Acceder a la documentación:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints Principales

- `POST /api/v1/chat/send-message`: Enviar mensaje al chatbot
- `POST /api/v1/chat/check-availability`: Verificar disponibilidad
- `POST /api/v1/chat/create-booking`: Crear reserva
- `POST /api/v1/webhooks/whatsapp`: Webhook para WhatsApp

## Despliegue en Railway

1. Crear nueva aplicación en Railway
2. Conectar con el repositorio de GitHub
3. Configurar variables de entorno en Railway:
   - `OPENAI_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - Otras variables específicas del proyecto

El despliegue se realizará automáticamente cuando se haga push al repositorio.

## Estructura del Proyecto

```
travel-chatbot-server/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── chat.py
│   │       └── webhooks.py
│   ├── core/
│   │   ├── chatbot.py
│   │   └── supabase.py
│   ├── models/
│   │   └── schemas.py
│   └── main.py
├── requirements.txt
├── Procfile
└── README.md
```

## Contribuir

1. Fork el repositorio
2. Crear rama para feature: `git checkout -b feature/nueva-caracteristica`
3. Commit cambios: `git commit -am 'Agregar nueva característica'`
4. Push a la rama: `git push origin feature/nueva-caracteristica`
5. Crear Pull Request

## Licencia

Este proyecto está bajo la licencia MIT.
