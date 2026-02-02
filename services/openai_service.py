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
    
    def _build_prompt(self, user_message: str, context: Dict = None) -> Tuple[str, str]:
        """Строит полный промпт для OpenAI"""
        
        # Более короткий и гибкий системный промпт
        system_prompt = f"""Ты — Анна, виртуальный консультант клиники пластической хирургии "{settings.clinic_name}".

Твой стиль:
- Дружелюбный, естественный, не роботизированный
- Отвечай конкретно на заданный вопрос
- Будь полезной, но не навязчивой
- Используй эмпатию и понимание

Правила:
1. Отвечай прямо на вопрос пользователя (1-3 предложения)
2. Если вопрос об услугах - давай краткую информацию и предлагай консультацию
3. Если вопрос не по теме - вежливо переведи на тему услуг клиники
4. Не используй шаблонные маркетинговые фразы каждый раз
5. Учитывай контекст и историю диалога
6. МАКСИМАЛЬНАЯ ДЛИНА ОТВЕТА: 1000 символов!

Контактная информация:
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
        
        # Формируем сообщение для пользователя
        full_user_message = f"""ВОПРОС КЛИЕНТА:
{user_message}

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
                temperature=0.7,
                max_tokens=500,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1
            )
            
            if response.choices:
                return response.choices[0].message.content.strip()
            else:
                logger.error("No choices in OpenAI response")
                return None
                
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
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


class FallbackService:
    """Улучшенный сервис для ответов на часто задаваемые вопросы"""
    
    def __init__(self):
        self.faq_responses = {
            "привет": [
                "Здравствуйте! Рад помочь вам с вопросами о наших услугах. Что вас интересует?",
                "Добрый день! Я здесь, чтобы рассказать о нашей клинике. Чем могу быть полезна?",
                "Приветствую! Готова ответить на ваши вопросы о пластической хирургии."
            ],
            "понимаешь": [
                "Да, я прекрасно понимаю вас! Я здесь, чтобы помочь и ответить на все вопросы.",
                "Конечно, понимаю! Могу рассказать о наших услугах или ответить на другие вопросы.",
                "Да, понимаю! Чем могу помочь сегодня?"
            ],
            "цена": [
                "Стоимость зависит от конкретной процедуры и индивидуальных особенностей. Давайте обсудим на бесплатной консультации?",
                "Цены варьируются в зависимости от объема работы. Могу предложить записаться на консультацию для точного расчета.",
                "У нас индивидуальный подход к ценообразованию. Хотите узнать подробнее о конкретной услуге?"
            ],
            "риск": [
                "Все процедуры проводятся опытными хирургами с минимизацией рисков. Расскажу подробнее на консультации!",
                "Безопасность - наш приоритет. Используем современные методики с минимальными осложнениями.",
                "Риски есть у любой процедуры, но мы их минимизируем благодаря опыту наших специалистов."
            ],
            "заразиться": [
                "Инфекции крайне редки благодаря строгим стандартам стерильности и современному оборудованию. Наша клиника соответствует всем нормам безопасности.",
                "Благодаря современным протоколам и стерильным условиям риск инфекции минимален. Мы уделяем этому особое внимание.",
                "Инфекционные осложнения составляют менее 1% благодаря нашему опыту и современным методикам."
            ],
            "консультация": [
                "Консультация у нас бесплатная! Запишитесь в удобное время, и врач все подробно расскажет.",
                "Да, мы предлагаем бесплатную первичную консультацию. Когда вам было бы удобно прийти?",
                "Консультация бесплатная и ни к чему не обязывает. Звоните для записи!"
            ],
            "длительность": [
                "Процедура обычно занимает 1-2 часа в зависимости от сложности. Реабилитация короткая.",
                "Время зависит от конкретной процедуры, но в среднем 1-2 часа. Хотите узнать подробнее?",
                "Большинство процедур занимают до 2 часов. После потребуется неделя на восстановление."
            ]
        }
    
    async def get_fallback_response(self, message: str) -> Optional[str]:
        """Возвращает ответ на основе ключевых слов"""
        message_lower = message.lower()
        
        # Проверяем ключевые слова
        for keyword, responses in self.faq_responses.items():
            if keyword in message_lower:
                import random
                return random.choice(responses)
        
        # Если нет конкретного ключевого слова, даем общий ответ
        general_responses = [
            "Это интересный вопрос! Лучше всего обсудить это лично на консультации с нашим специалистом.",
            "Понимаю ваш интерес к этой теме. Могу предложить бесплатную консультацию для детальной информации.",
            "Хороший вопрос! Для точной информации рекомендую консультацию с нашим врачом.",
            "Давайте обсудим это на консультации? Специалист сможет дать исчерпывающую информацию."
        ]
        
        import random
        return random.choice(general_responses)


# Глобальные экземпляры сервисов
openai_service = OpenAIService()
fallback_service = FallbackService()
