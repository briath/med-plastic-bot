import asyncio
import logging
from typing import Dict, Optional, List
from services.parser import WebsiteParser
from models.repositories import ServiceRepository

logger = logging.getLogger(__name__)


class WebsiteContentService:
    """Сервис для получения контента с сайта клиники и интеграции в GPT"""
    
    def __init__(self):
        self.parser = WebsiteParser()
        self.cached_content = {}
        self.service_urls = {
            "блефаропластика": "https://med-plastic.ru/plastika-verhnih-vek/",
            "пластика век": "https://med-plastic.ru/plastika-verhnih-vek/",
            "верхние века": "https://med-plastic.ru/plastika-verhnih-vek/",
            "пластика верхних век": "https://med-plastic.ru/plastika-verhnih-vek/",
            # Можно добавить другие услуги по мере необходимости
        }
    
    async def get_service_content(self, service_name: str) -> Optional[Dict]:
        """Получает контент для конкретной услуги"""
        # Проверяем кэш
        if service_name in self.cached_content:
            return self.cached_content[service_name]
        
        # Ищем URL для услуги
        url = self._find_service_url(service_name)
        if not url:
            logger.warning(f"No URL found for service: {service_name}")
            return None
        
        try:
            # Парсим страницу
            content = await self.parser.parse_service_page(url)
            if content:
                # Кэшируем результат
                self.cached_content[service_name] = content
                logger.info(f"Successfully cached content for {service_name}")
                return content
            else:
                logger.warning(f"Failed to parse content for {service_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting service content for {service_name}: {e}")
            return None
    
    def _find_service_url(self, service_name: str) -> Optional[str]:
        """Находит URL для услуги по ключевым словам"""
        service_name_lower = service_name.lower()
        
        for keywords, url in self.service_urls.items():
            if keywords in service_name_lower:
                return url
        
        return None
    
    async def get_relevant_content_for_query(self, query: str) -> Optional[str]:
        """Получает релевантный контент для запроса"""
        query_lower = query.lower()
        
        # Проверяем, относится ли запрос к услугам с сайта
        for keywords in self.service_urls.keys():
            if keywords in query_lower:
                content = await self.get_service_content(keywords)
                if content:
                    return self._format_content_for_gpt(content)
        
        return None
    
    def _format_content_for_gpt(self, content: Dict) -> str:
        """Форматирует контент для использования в GPT промпте"""
        formatted = f"""
ИНФОРМАЦИЯ С САЙТА КЛИНИКИ:

Название услуги: {content.get('name', '')}

Описание: {content.get('description', '')}

Показания: {content.get('indications', '')}

Методики проведения: {content.get('methods', '')}

Длительность: {content.get('duration', '')}

Реабилитация: {content.get('recovery', '')}

Стоимость: {content.get('price_range', '')}

Источник: {content.get('source_url', '')}
"""
        return formatted.strip()
    
    async def preload_all_services(self):
        """Предзагружает контент всех услуг"""
        logger.info("Preloading service content...")
        for service_name in self.service_urls.keys():
            await self.get_service_content(service_name)
        logger.info(f"Preloaded {len(self.cached_content)} services")


# Глобальный экземпляр
website_content_service = WebsiteContentService()
