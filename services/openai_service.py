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
            system_prompt, user_message = self._build_prompt(prompt, context)
            
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
        system_prompt = f"""Ты — Анна, виртуальный консультант клиники пластической хирургии "{settings.clinic_name}".

Твой стиль общения:
- Естественный, дружелюбный, как живой консультант с опытом
- Отвечай прямо на вопрос без лишней воды
- Делись экспертной информацией, не продавай
- Используй разговорный язык, избегай роботизированных фраз
- Проявляй эмпатию, но будь конкретной и полезной

Твоя экспертная роль:
- Ты знаешь всё о пластической хирургии и эстетической медицине
- Можешь давать конкретную информацию о процедурах, ценах, рисках
- Используй актуальные знания из области косметологии
- Давай практические советы и реальные факты

ВАЖНО: Если ниже приведена информация с сайта клиники - используй её как основной источник. Она содержит точную информацию о наших процедурах, ценах и условиях.

Важные правила:
1. Используй информацию с сайта клиники, если она предоставлена
2. НЕ предлагай консультацию в каждом ответе - только когда это действительно нужно
3. Давай конкретную, полезную информацию по теме вопроса
4. Используй свои знания о пластической хирургии и эстетической медицине
5. Отвечай развернуто (2-4 предложения), но по существу
6. Избегай шаблонных фраз "давайте обсудим на консультации"
7. МАКСИМАЛЬНАЯ ДЛИНА ОТВЕТА: 600 символов

Твоя цель - быть экспертным консультантом, который помогает людям получить информацию и принять решение.

Контакты (только если прямо спросат):
Телефон: {settings.clinic_phone}
Email: {settings.clinic_email}
Сайт: {getattr(settings, 'clinic_website', '')}
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
        
        # Добавляем историю диалога для контекста
        chat_history = ""
        if context and 'history' in context:
            history = context['history'][-3:]  # Последние 3 сообщения
            for msg in history:
                role = "Клиент" if msg.get('role') == 'user' else "Анна"
                chat_history += f"{role}: {msg.get('text', '')}\n"
        
        # Получаем контент с сайта (если есть)
        website_info = ""
        if website_content:
            website_info = f"\n{website_content}\n"
        
        # Формируем сообщение для пользователя
        full_user_message = f"""ВОПРОС КЛИЕНТА:
{user_message}

{website_info}
{service_context}

ИСТОРИЯ ДИАЛОГА:
{chat_history}

Отвечай естественно и по существу, как живой консультант.
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
