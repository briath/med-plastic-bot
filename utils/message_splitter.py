"""Утилиты для работы с сообщениями Telegram"""

from typing import List

def split_message(text: str, max_length: int = 4096) -> List[str]:
    """
    Разделяет длинное сообщение на части для Telegram
    
    Args:
        text: Текст сообщения
        max_length: Максимальная длина одной части
        
    Returns:
        Список частей сообщения
    """
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_part = ""
    
    # Разделяем по абзацам
    paragraphs = text.split('\n\n')
    
    for paragraph in paragraphs:
        # Если абзац сам по себе слишком длинный, разделяем его по предложениям
        if len(paragraph) > max_length:
            sentences = paragraph.split('. ')
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                # Добавляем точку если её нет
                if not sentence.endswith('.'):
                    sentence += '.'
                
                # Если добавление предложения превысит лимит
                if len(current_part) + len(sentence) + 2 > max_length:
                    if current_part:
                        parts.append(current_part.strip())
                        current_part = sentence
                    else:
                        # Предложение слишком длинное, режем по словам
                        words = sentence.split()
                        temp_sentence = ""
                        for word in words:
                            if len(temp_sentence) + len(word) + 1 > max_length:
                                if temp_sentence:
                                    parts.append(temp_sentence.strip())
                                    temp_sentence = word
                                else:
                                    # Слово слишком длинное, режем принудительно
                                    while len(word) > max_length:
                                        parts.append(word[:max_length])
                                        word = word[max_length:]
                                    temp_sentence = word
                            else:
                                temp_sentence += (" " if temp_sentence else "") + word
                        current_part = temp_sentence
                else:
                    current_part += (" " if current_part else "") + sentence
        else:
            # Если добавление абзаца превысит лимит
            if len(current_part) + len(paragraph) + 2 > max_length:
                if current_part:
                    parts.append(current_part.strip())
                    current_part = paragraph
                else:
                    # Абзац слишком длинный (маловероятно после проверки выше)
                    parts.append(paragraph[:max_length])
                    current_part = paragraph[max_length:]
            else:
                current_part += ("\n\n" if current_part else "") + paragraph
    
    # Добавляем последнюю часть
    if current_part:
        parts.append(current_part.strip())
    
    return parts


def truncate_message(text: str, max_length: int = 3500) -> str:
    """
    Обрезает сообщение до указанной длины с добавлением индикатора обрезки
    
    Args:
        text: Текст сообщения
        max_length: Максимальная длина
        
    Returns:
        Обрезанный текст
    """
    if len(text) <= max_length:
        return text
    
    # Находим последнее предложение для красивой обрезки
    truncated = text[:max_length]
    last_period = truncated.rfind('.')
    last_exclamation = truncated.rfind('!')
    last_question = truncated.rfind('?')
    
    # Берем последний конец предложения
    last_end = max(last_period, last_exclamation, last_question)
    
    if last_end > max_length - 100:  # Если конец предложения недалеко от конца
        truncated = truncated[:last_end + 1]
    
    return truncated + "...\n\n(ответ сокращен для отображения в Telegram)"
