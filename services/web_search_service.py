import asyncio
import logging
import aiohttp
from typing import Optional, List, Dict
from urllib.parse import quote_plus
import re

logger = logging.getLogger(__name__)


class WebSearchService:
    """Сервис для поиска информации в интернете"""
    
    def __init__(self):
        # Используем DuckDuckGo API (не требует ключа)
        self.search_url = "https://api.duckduckgo.com/"
        self.backup_search_url = "https://html.duckduckgo.com/html/"
    
    async def search_medical_info(self, query: str) -> Optional[str]:
        """Ищет медицинскую информацию по запросу"""
        try:
            # Формируем поисковый запрос с учетом медицинской тематики
            medical_query = f"{query} пластическая хирургия эстетическая медицина"
            
            # Пробуем основной API
            result = await self._search_duckduckgo(medical_query)
            
            if result:
                return self._format_medical_response(result, query)
            
            # Если основной не сработал, пробуем backup
            result = await self._search_duckduckgo_html(medical_query)
            
            if result:
                return self._format_medical_response(result, query)
                
            return None
            
        except Exception as e:
            logger.error(f"Error searching medical info: {e}")
            return None
    
    async def _search_duckduckgo(self, query: str) -> Optional[Dict]:
        """Поиск через DuckDuckGo API"""
        try:
            params = {
                'q': query,
                'format': 'json',
                'no_html': 1,
                'skip_disambig': 1
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(self.search_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    return None
                    
        except Exception as e:
            logger.error(f"DuckDuckGo API error: {e}")
            return None
    
    async def _search_duckduckgo_html(self, query: str) -> Optional[List[str]]:
        """Поиск через HTML версию DuckDuckGo"""
        try:
            params = {
                'q': query,
                'kl': 'ru-ru'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(self.backup_search_url, params=params, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_html_results(html)
                    return None
                    
        except Exception as e:
            logger.error(f"DuckDuckGo HTML error: {e}")
            return None
    
    def _parse_html_results(self, html: str) -> List[str]:
        """Парсит HTML результаты поиска"""
        results = []
        
        # Ищем результаты в HTML
        pattern = r'<a[^>]*class="result__a"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.IGNORECASE)
        
        for match in matches[:3]:  # Берем первые 3 результата
            # Очищаем от HTML тегов
            clean_text = re.sub(r'<[^>]+>', '', match)
            if len(clean_text) > 20:  # Пропускаем слишком короткие
                results.append(clean_text.strip())
        
        return results
    
    def _format_medical_response(self, search_data, original_query: str) -> str:
        """Форматирует найденную информацию в естественный ответ"""
        
        if isinstance(search_data, dict) and 'AbstractText' in search_data:
            # Если есть краткое описание
            abstract = search_data.get('AbstractText', '')
            if abstract and len(abstract) > 50:
                return f"По вашему вопросу нашла информацию: {abstract[:200]}... Хотите узнать подробнее?"
        
        if isinstance(search_data, list):
            # Если это список результатов
            if search_data:
                first_result = search_data[0]
                return f"Интересный вопрос! По теме '{original_query}' нашла, что {first_result.lower()[:150]}... Могу рассказать подробнее, если интересно."
        
        # Если ничего не подошло
        return f"По вашему вопросу '{original_query}' есть разная информация. В пластической хирургии это зависит от многих факторов. Хотите обсудить конкретный аспект?"


# Глобальный экземпляр
web_search_service = WebSearchService()
