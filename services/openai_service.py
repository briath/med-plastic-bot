import asyncio
import logging
from typing import Optional, Dict, List, Tuple
import json
from openai import AsyncOpenAI
from config.settings import settings

logger = logging.getLogger(__name__)


class OpenAIService:
    """Сервис для работы с OpenAI GPT-4o-mini"""
    
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.base_url = getattr(settings, 'openai_base_url', 'https://api.openai.com/v1')
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    async def generate_response(self, prompt: str, context: Dict = None) -> Optional[str]:
        """Генерирует ответ с помощью OpenAI GPT-4o-mini"""
        try:
            # Формируем полный промпт
            system_prompt, user_message = await self._build_prompt(prompt, context)
            
            # Отправляем запрос к OpenAI
            response = await self._call_openai(system_prompt, user_message, context)
            
            if response:
                # Ограничиваем длину ответа (Telegram ограничение ~4096 символов)
                max_length = 3500  # Оставляем запас
                if len(response) > max_length:
                    response = response[:max_length] + "...\n\n(ответ сокращен для отображения в Telegram)"
                logger.info(f"OpenAI response generated successfully")
                return response
            else:
                logger.warning("Empty response from OpenAI")
                return None
                
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            return None
    
    async def _build_prompt(self, user_message: str, context: Dict = None) -> Tuple[str, str]:
        """Строит полный промпт для OpenAI"""
        
        # Проверяем, есть ли релевантный контент с сайта
        from services.website_content_service import website_content_service
        website_content = await website_content_service.get_relevant_content_for_query(user_message)
        
        # Более короткий и гибкий системный промпт
        system_prompt = f"""Ты - умный ассистент. ОТВЕЧАЙ ТОЛЬКО НА ЗАДАННЫЙ ВОПРОС.

СТРОГИЕ ПРАВИЛА:
1. ОТВЕЧАЙ ИМЕННО НА ТОТ ВОПРОС, КОТОРЫЙ ЗАДАЛИ
2. НЕ ДОБАВЛЯЙ "Анна:" или другие префиксы
3. НЕ УПОМИНАЙ ПЛАСТИЧЕСКУЮ ХИРУРГИЮ, если вопрос не о ней
4. БУДЬ КРАТКИМ (макс. 200 символов)
5. НЕ ПРЕДЛАГАЙ ПОМОЩЬ, если не спрашивают

ПРИМЕРЫ:
Вопрос: "какая столица у Парижа?"
Ответ: "Париж - это столица Франции."

Вопрос: "Какая площадь африки?"
Ответ: "Площадь Африки - около 30,3 млн км²."

Вопрос: "Что такое блефаропластика?"
Ответ: "Блефаропластика - операция по коррекции век. Цена от 50 000 руб."

ОТВЕЧАЙ ТОЧНО И КРАТКО!
"""
        
        # Добавляем контекст об услуге только если релевантно
        service_context = ""
        if context and 'service' in context:
            service = context['service']
            # Добавляем только краткую информацию
            service_context = f"""
Краткая информация об услуге:
Название: {service.get('name', '')}
Цены: {service.get('price_range', '')}
Длительность: {service.get('duration', '')}
"""
        
        # Добавляем историю диалога для контекста (только для медицинских вопросов)
        chat_history = ""
        if context and 'history' in context:
            # Добавляем историю только если вопрос о медицине
            medical_keywords = ['пластик', 'хирург', 'операция', 'блефаропластика', 'грудь', 'лицо']
            if any(keyword in user_message.lower() for keyword in medical_keywords):
                history = context['history'][-2:]  # Последние 2 сообщения
                for msg in history:
                    role = "Клиент" if msg.get('role') == 'user' else "Анна"
                    chat_history += f"{role}: {msg.get('text', '')}\n"
        
        # Получаем контент с сайта (если есть)
        website_info = ""
        if website_content:
            website_info = f"\n{website_content}\n"
        
        # Формируем сообщение для пользователя
        full_user_message = f"""ВОПРОС: {user_message}

{website_info}
{service_context}

{chat_history}

ОТВЕТЬ ТОЛЬКО НА ЭТОТ ВОПРОС: "{user_message}"
"""
        
        return system_prompt, full_user_message
    
    async def _call_openai(self, system_prompt: str, user_message: str, context: Dict = None) -> Optional[str]:
        """Отправляет запрос к OpenAI API"""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,  # Увеличиваем для более креативных ответов
                max_tokens=600,    # Увеличиваем для развернутых ответов
                top_p=0.9,
                frequency_penalty=0.2,  # Уменьшаем повторения
                presence_penalty=0.2
            )
            
            if response.choices:
                result = response.choices[0].message.content.strip()
                logger.info(f"OpenAI response generated successfully, length: {len(result)}")
                return result
            else:
                logger.error("No choices in OpenAI response")
                return None
                
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            # Проверяем тип ошибки для лучшей обработки
            if "403" in str(e):
                logger.warning("OpenAI API key issue or region restriction")
            elif "429" in str(e):
                logger.warning("OpenAI rate limit exceeded")
            return None
    
    async def check_connection(self) -> bool:
        """Проверяет доступность OpenAI"""
        try:
            response = await self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"OpenAI connection check failed: {e}")
            return False
    
    async def get_available_models(self) -> List[str]:
        """Получает список доступных моделей"""
        try:
            response = await self.client.models.list()
            return [model.id for model in response.data if 'gpt' in model.id]
        except Exception as e:
            logger.error(f"Failed to get OpenAI models: {e}")
            return []


# Глобальные экземпляры сервисов
openai_service = OpenAIService()
# fallback_service удален - используем только GPT-4o-mini и веб-поиск
