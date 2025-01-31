from typing import Dict
from app.core.chatbot import ChatbotManager

# Almacenar instancias activas de chatbots
active_chatbots: Dict[str, ChatbotManager] = {}

def get_active_chatbots() -> Dict[str, ChatbotManager]:
    """
    Retorna el diccionario de chatbots activos
    """
    return active_chatbots
