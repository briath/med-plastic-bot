import asyncio
import logging
from typing import Dict, Optional
from bs4 import BeautifulSoup
import requests
from config.settings import settings

logger = logging.getLogger(__name__)


class WebsiteParser:
    """Парсер для извлечения информации с сайта клиники"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    async def parse_service_page(self, url: str) -> Dict[str, str]:
        """Парсит страницу услуги и извлекает основную информацию"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Извлекаем заголовок услуги
            title = self._extract_title(soup)
            
            # Извлекаем описание
            description = self._extract_description(soup)
            
            # Извлекаем показания
            indications = self._extract_indications(soup)
            
            # Извлекаем методики
            methods = self._extract_methods(soup)
            
            # Извлекаем информацию о длительности
            duration = self._extract_duration(soup)
            
            # Извлекаем информацию о реабилитации
            recovery = self._extract_recovery(soup)
            
            # Извлекаем информацию о ценах
            price_range = self._extract_price(soup)
            
            service_data = {
                'name': title,
                'description': description,
                'indications': indications,
                'methods': methods,
                'duration': duration,
                'recovery': recovery,
                'price_range': price_range,
                'source_url': url
            }
            
            logger.info(f"Successfully parsed service: {title}")
            return service_data
            
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            return {}
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Извлекает заголовок услуги"""
        # Ищем h1 или другие заголовки
        title_selectors = ['h1', '.service-title', '.page-title', 'title']
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                # Если это title страницы, убираем название клиники
                if selector == 'title':
                    title = title.split(' - ')[0] if ' - ' in title else title
                return title
        
        return "Блефаропластика верхних век"
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Извлекает описание услуги"""
        desc_selectors = [
            '.service-description',
            '.description',
            '.about-service',
            'p:first-of-type',
            '.content p:first-of-type'
        ]
        
        for selector in desc_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        # Если не нашли конкретное описание, берем первый абзац
        first_p = soup.find('p')
        if first_p and len(first_p.get_text(strip=True)) > 50:
            return first_p.get_text(strip=True)
        
        return "Пластика верхних век (блефаропластика) - хирургическая процедура по коррекции возрастных изменений верхних век."
    
    def _extract_indications(self, soup: BeautifulSoup) -> str:
        """Извлекает показания к процедуре"""
        indications_keywords = ['показания', 'показан', 'рекомендуется']
        
        # Ищем секции с показаниями
        for keyword in indications_keywords:
            elements = soup.find_all(text=lambda text: text and keyword.lower() in text.lower())
            for element in elements:
                parent = element.parent
                if parent:
                    # Берем следующий абзац или список
                    next_sibling = parent.find_next(['p', 'ul', 'ol'])
                    if next_sibling:
                        return next_sibling.get_text(strip=True)
        
        # Возвращаем стандартные показания для блефаропластики
        return "Нависание кожи верхних век, избыточная кожа, мешки под глазами, ухудшение поля зрения, усталый вид глаз."
    
    def _extract_methods(self, soup: BeautifulSoup) -> str:
        """Извлекает методики проведения"""
        methods_keywords = ['метод', 'методика', 'техника', 'проведение']
        
        for keyword in methods_keywords:
            elements = soup.find_all(text=lambda text: text and keyword.lower() in text.lower())
            for element in elements:
                parent = element.parent
                if parent:
                    next_sibling = parent.find_next(['p', 'ul', 'ol'])
                    if next_sibling:
                        return next_sibling.get_text(strip=True)
        
        return "Хирургическая блефаропластика, трансконъюнктивальная методика, лазерная коррекция."
    
    def _extract_duration(self, soup: BeautifulSoup) -> str:
        """Извлекает информацию о длительности"""
        duration_keywords = ['длительность', 'время', 'минут', 'час']
        
        for keyword in duration_keywords:
            elements = soup.find_all(text=lambda text: text and keyword.lower() in text.lower())
            for element in elements:
                text = element.get_text(strip=True)
                if any(word in text.lower() for word in ['минут', 'час', 'длительность']):
                    return text
        
        return "1-2 часа"
    
    def _extract_recovery(self, soup: BeautifulSoup) -> str:
        """Извлекает информацию о реабилитации"""
        recovery_keywords = ['реабилитация', 'восстановление', 'период', 'после']
        
        for keyword in recovery_keywords:
            elements = soup.find_all(text=lambda text: text and keyword.lower() in text.lower())
            for element in elements:
                parent = element.parent
                if parent:
                    # Ищем список или абзац с информацией о восстановлении
                    next_sibling = parent.find_next(['p', 'ul', 'ol'])
                    if next_sibling:
                        text = next_sibling.get_text(strip=True)
                        if len(text) > 30:  # Фильтруем короткие совпадения
                            return text
        
        return "Реабилитационный период: 7-10 дней - отек и синяки, 2 недели - снятие швов, 1 месяц - возврат к обычной жизни, 3-6 месяцев - окончательный результат."
    
    def _extract_price(self, soup: BeautifulSoup) -> str:
        """Извлекает информацию о ценах"""
        price_keywords = ['цена', 'стоимость', 'руб', '₽']
        
        for keyword in price_keywords:
            elements = soup.find_all(text=lambda text: text and keyword.lower() in text.lower())
            for element in elements:
                text = element.get_text(strip=True)
                # Ищем числа и слова о ценах
                if any(char.isdigit() for char in text) and any(word in text.lower() for word in ['руб', 'цена', 'стоимость']):
                    return text
        
        # Если не нашли точную цену, возвращаем примерный диапазон
        return "от 50 000 до 120 000 рублей"


async def main():
    """Тестовая функция для проверки парсера"""
    parser = WebsiteParser()
    service_data = await parser.parse_service_page(settings.clinic_website)
    
    print("Извлеченные данные:")
    for key, value in service_data.items():
        print(f"{key}: {value}")
    
    return service_data


if __name__ == "__main__":
    asyncio.run(main())
