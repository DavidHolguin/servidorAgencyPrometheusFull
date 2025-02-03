from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class WeightSystem:
    """Sistema de pesos para optimizar las respuestas del chatbot"""
    
    def __init__(self):
        # Pesos base para elementos del context_structure
        self.context_structure_weights = {
            'tone': 0.10,
            'purpose': 0.25,
            'example_qa': 0.15,
            'key_points': 0.20,
            'special_instructions': 0.30
        }
        
        # Pesos para otros elementos del chatbot
        self.chatbot_weights = {
            'quick_questions': 0.35,  # Mayor peso para quick_questions
            'personality': 0.15,
            'context': 0.20,
            'configuration': 0.15,
            'voice_enabled': 0.05,
            'use_emojis': 0.05,
            'welcome_message': 0.05
        }
    
    def calculate_context_relevance(self, context_structure: Dict[str, Any]) -> float:
        """
        Calcula la relevancia del contexto basado en los pesos definidos
        
        Args:
            context_structure: Estructura del contexto del chatbot
            
        Returns:
            float: Score de relevancia (0-1)
        """
        relevance_score = 0.0
        
        for key, weight in self.context_structure_weights.items():
            if key in context_structure and context_structure[key]:
                # Añadir peso si el elemento existe y tiene contenido
                relevance_score += weight
                
        return min(relevance_score, 1.0)
    
    def calculate_response_weights(self, chatbot_config: Dict[str, Any]) -> Dict[str, float]:
        """
        Calcula los pesos para la generación de respuestas
        
        Args:
            chatbot_config: Configuración completa del chatbot
            
        Returns:
            Dict[str, float]: Pesos calculados para cada componente
        """
        weights = {}
        
        # Procesar quick_questions (prioridad alta)
        if 'quick_questions' in chatbot_config and chatbot_config['quick_questions']:
            weights['quick_questions'] = self.chatbot_weights['quick_questions']
            
        # Procesar personality y context
        if chatbot_config.get('personality'):
            weights['personality'] = self.chatbot_weights['personality']
        if chatbot_config.get('context'):
            weights['context'] = self.chatbot_weights['context']
            
        # Procesar configuración general
        if chatbot_config.get('configuration'):
            weights['configuration'] = self.chatbot_weights['configuration']
            
        # Procesar características específicas
        weights['voice_enabled'] = (
            self.chatbot_weights['voice_enabled'] 
            if chatbot_config.get('voice_enabled') 
            else 0.0
        )
        weights['use_emojis'] = (
            self.chatbot_weights['use_emojis'] 
            if chatbot_config.get('use_emojis') 
            else 0.0
        )
        
        # Normalizar pesos para que sumen 1
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v/total_weight for k, v in weights.items()}
            
        return weights
    
    def apply_weights_to_response(
        self, 
        response: str, 
        chatbot_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Aplica los pesos al proceso de generación de respuesta
        
        Args:
            response: Respuesta original
            chatbot_config: Configuración del chatbot
            
        Returns:
            Dict con la respuesta procesada y metadatos
        """
        weights = self.calculate_response_weights(chatbot_config)
        context_structure = chatbot_config.get('context_structure', {})
        context_relevance = self.calculate_context_relevance(context_structure)
        
        # Aplicar pesos a la respuesta
        enhanced_response = {
            'text': response,
            'weights_applied': weights,
            'context_relevance': context_relevance,
            'metadata': {
                'quick_questions_priority': weights.get('quick_questions', 0),
                'personality_influence': weights.get('personality', 0),
                'context_influence': weights.get('context', 0)
            }
        }
        
        return enhanced_response
