# app/api/v1/webhooks.py
from fastapi import APIRouter, HTTPException, Header, Request
from app.models.schemas import WhatsAppMessage
from app.core.chatbot import ChatbotManager

router = APIRouter()

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Header(None),
    hub_verify_token: str = Header(None),
    hub_challenge: str = Header(None)
):
    if hub_verify_token == settings.whatsapp_verify_token:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Invalid verify token")

@router.post("/webhook")
async def webhook_handler(request: Request):
    body = await request.json()
    
    # Procesar mensaje de WhatsApp
    if body.get("object") == "whatsapp_business_account":
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("value", {}).get("messages"):
                    message = change["value"]["messages"][0]
                    phone_number = message["from"]
                    message_text = message["text"]["body"]
                    
                    # Aquí deberías tener una forma de mapear el número de teléfono
                    # con un chatbot_id específico
                    chatbot = ChatbotManager("default_chatbot_id")
                    response = await chatbot.process_message(message_text)
                    
                    # Aquí implementarías el envío de la respuesta vía WhatsApp API
                    
    return {"status": "success"}