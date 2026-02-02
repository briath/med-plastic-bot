"""Утилиты для безопасной отправки сообщений в Telegram"""

import asyncio
import logging
from aiogram import types
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter, TelegramBadRequest
from functools import wraps
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def safe_send_message(message: types.Message, text: str, **kwargs) -> bool:
    """
    Безопасная отправка сообщения с обработкой сетевых ошибок
    
    Args:
        message: Объект сообщения для ответа
        text: Текст сообщения
        **kwargs: Дополнительные параметры отправки
        
    Returns:
        True если сообщение отправлено успешно, False в противном случае
    """
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            await message.answer(text, **kwargs)
            return True
            
        except TelegramRetryAfter as e:
            logger.warning(f"Rate limit exceeded, waiting {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after)
            continue
            
        except TelegramNetworkError as e:
            logger.warning(f"Network error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (2 ** attempt))  # Экспоненциальный бэк-офф
                continue
            else:
                logger.error(f"Failed to send message after {max_retries} attempts")
                return False
                
        except TelegramBadRequest as e:
            if "message is too long" in str(e):
                # Если сообщение слишком длинное, пытаемся сократить
                if len(text) > 4000:
                    shortened_text = text[:4000] + "...\n\n(сообщение сокращено)"
                    try:
                        await message.answer(shortened_text, **kwargs)
                        return True
                    except Exception as final_error:
                        logger.error(f"Failed to send shortened message: {final_error}")
                        return False
            logger.error(f"Bad request error: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")
            return False
    
    return False


async def safe_send_messages(message: types.Message, texts: List[str], **kwargs) -> bool:
    """
    Безопасная отправка нескольких сообщений
    
    Args:
        message: Объект сообщения для ответа
        texts: Список текстов сообщений
        **kwargs: Дополнительные параметры отправки
        
    Returns:
        True если все сообщения отправлены успешно
    """
    success = True
    for i, text in enumerate(texts):
        if not await safe_send_message(message, text, **kwargs):
            logger.error(f"Failed to send message {i + 1}/{len(texts)}")
            success = False
            # Небольшая задержка перед следующей попыткой
            await asyncio.sleep(0.5)
    
    return success


def safe_message_handler(func):
    """
    Декоратор для безопасной обработки сообщений с автоматическим созданием пользователя
    """
    @wraps(func)
    async def wrapper(message_or_callback, session: AsyncSession, *args, **kwargs):
        try:
            return await func(message_or_callback, session, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in handler {func.__name__}: {e}", exc_info=True)
            
            # Пытаемся отправить сообщение об ошибке
            error_text = "😔 Произошла ошибка. Пожалуйста, попробуйте еще раз."
            
            if hasattr(message_or_callback, 'message'):
                # Это callback query
                await safe_send_message(message_or_callback.message, error_text)
            else:
                # Это обычное сообщение
                await safe_send_message(message_or_callback, error_text)
    
    return wrapper
