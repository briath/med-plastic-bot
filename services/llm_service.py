import asyncio
import logging
from typing import Optional, Dict, List
import json
import requests
from config.settings import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Сервис для работы с локальной языковой моделью (Ollama)"""
    
    def __init__(self):
        self.host = settings.ollama_host
        self.model = settings.ollama_model
        self.base_url = f"{self.host}/api"
    
    async def generate_response(self, prompt: str, context: Dict = None) -> Optional[str]:
        """Генерирует ответ с помощью LLM"""
        try:
            # Формируем полный промпт
            full_prompt = self._build_prompt(prompt, context)
            
            # Отправляем запрос к Ollama
            response = await self._call_ollama(full_prompt)
            
            if response:
                logger.info(f"LLM response generated successfully")
                return response
            else:
                logger.warning("Empty response from LLM")
                return None
                
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return None
    
    def _build_prompt(self, user_message: str, context: Dict = None) -> str:
        """Строит полный промпт для LLM"""
        
        # Базовая роль и стиль
        system_prompt = f"""Ты — Анна, виртуальный помощник клиники пластической хирургии "{settings.clinic_name}".
Твой стиль общения: дружелюбный, профессиональный, сочувствующий, но без излишней фамильярности.
Ты даешь точные медицинские информацию, но всегда уточняешь, что окончательный ответ может дать только хирург на консультации.

Правила:
1. Отвечай кратко (2-5 предложений)
2. Используй эмпатичные фразы ("Понимаю ваш интерес", "Это хороший вопрос")
3. Не выдумывай информацию, которой нет в контексте
4. Если не знаешь ответа, предложи связаться с живым менеджером
5. Завершай ответ вопросом или предложением помощи
"""
        
        # Добавляем контекст об услуге
        service_context = ""
        if context and 'service' in context:
            service = context['service']
            service_context = f"""
Контекст об услуге:
Название: {service.get('name', 'Блефаропластика верхних век')}
Описание: {service.get('description', '')}
Показания: {service.get('indications', '')}
Методики: {service.get('methods', '')}
Длительность: {service.get('duration', '')}
Реабилитация: {service.get('recovery', '')}
Цены: {service.get('price_range', '')}
"""
        
        # Добавляем историю диалога
        chat_history = ""
        if context and 'history' in context:
            history = context['history'][-3:]  # Последние 3 сообщения
            for msg in history:
                role = "Пользователь" if msg.get('role') == 'user' else "Анна"
                chat_history += f"{role}: {msg.get('text', '')}\n"
        
        # Собираем полный промпт
        full_prompt = f"""{system_prompt}

{service_context}

История диалога:
{chat_history}

Текущий вопрос пользователя:
{user_message}

Ответ Анны (2-5 предложений, закончи эмпатичной фразой или вопросом):
"""
        
        return full_prompt
    
    async def _call_ollama(self, prompt: str) -> Optional[str]:
        """Отправляет запрос к Ollama API"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 200
                }
            }
            
            # Отправляем запрос
            response = requests.post(
                f"{self.base_url}/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("Timeout when calling Ollama API")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("Connection error when calling Ollama API. Is Ollama running?")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling Ollama: {e}")
            return None
    
    async def check_connection(self) -> bool:
        """Проверяет доступность Ollama"""
        try:
            response = requests.get(f"{self.base_url}/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    async def get_available_models(self) -> List[str]:
        """Получает список доступных моделей"""
        try:
            response = requests.get(f"{self.base_url}/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except:
            return []


class FallbackService:
    """Сервис для ответов на часто задаваемые вопросы без LLM"""
    
    def __init__(self):
        self.faq_responses = {
            "цена": [
                "Стоимость блефаропластики зависит от сложности и методики. Ориентировочно от 50 000 до 120 000 рублей. Точную цену назовет хирург после консультации.",
                "Цена на блефаропластику верхних век варьируется в зависимости от объема работы. Хотите узнать подробнее о конкретной методике?"
            ],
            "длительность": [
                "Операция длится от 1 до 2 часов, в зависимости от сложности и выбранной методики.",
                "Блефаропластика занимает около 1-2 часов. После операции потребуется некоторое время на наблюдение."
            ],
            "реабилитация": [
                "Реабилитация занимает 7-10 дней для заживления, 2 недели для снятия швов, 1 месяц для возврата к обычной жизни. Окончательный результат через 3-6 месяцев.",
                "После операции первые 7-10 дней будет отек, затем 2 недели снимают швы. Через месяц можно вернуться к обычной жизни."
            ],
            "риск": [
                "Как и любая операция, блефаропластика имеет риски: асимметрия, сухость глаз, гематома. В нашей клинике риск минимизирован за счет опыта хирургов.",
                "Риски включают асимметрию, сухость глаз, редкие осложнения. Наши хирурги минимизируют риски благодаря большому опыту."
            ],
            "подготовка": [
                "Перед операцией требуется консультация хирурга, анализы и отказ от некоторых лекарств. Подробности расскажет врач на консультации.",
                "Необходима предварительная консультация, сдача анализов и подготовка по рекомендациям врача."
            ]
        }
    
    async def get_fallback_response(self, message: str) -> Optional[str]:
        """Возвращает ответ на основе ключевых слов"""
        message_lower = message.lower()
        
        for keyword, responses in self.faq_responses.items():
            if keyword in message_lower:
                # Возвращаем случайный ответ из списка
                import random
                return random.choice(responses)
        
        return None


# Глобальные экземпляры сервисов
llm_service = LLMService()
fallback_service = FallbackService()
