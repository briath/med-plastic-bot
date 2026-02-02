import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from services.openai_service import OpenAIService, FallbackService


class TestOpenAIService:
    """Тесты для OpenAI сервиса"""
    
    @pytest.mark.asyncio
    async def test_generate_response_success(self):
        """Тест успешной генерации ответа"""
        service = OpenAIService()
        
        # Мокаем OpenAI клиент
        with patch('services.openai_service.AsyncOpenAI') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            
            # Мокаем ответ от OpenAI
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content="Тестовый ответ от OpenAI"))
            ]
            mock_instance.chat.completions.create.return_value = mock_response
            
            result = await service.generate_response(
                "Тестовый вопрос",
                {'service': {'name': 'Блефаропластика'}}
            )
            
            assert result == 'Тестовый ответ от OpenAI'
            mock_instance.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_response_error(self):
        """Тест генерации ответа с ошибкой"""
        service = OpenAIService()
        
        # Мокаем OpenAI клиент с ошибкой
        with patch('services.openai_service.AsyncOpenAI') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            mock_instance.chat.completions.create.side_effect = Exception("OpenAI API error")
            
            result = await service.generate_response("Тестовый вопрос")
            
            assert result is None
    
    def test_build_prompt(self):
        """Тест построения промпта"""
        service = OpenAIService()
        
        system_prompt, user_message = service._build_prompt(
            "Какая цена?",
            {
                'service': {
                    'name': 'Блефаропластика',
                    'price_range': 'от 50 000 руб'
                },
                'history': [
                    {'role': 'user', 'text': 'Привет'},
                    {'role': 'assistant', 'text': 'Здравствуйте'}
                ]
            }
        )
        
        assert "Анна" in system_prompt
        assert "менеджер по продажам" in system_prompt
        assert "Блефаропластика" in user_message
        assert "Какая цена?" in user_message
        assert "от 50 000 руб" in user_message
    
    @pytest.mark.asyncio
    async def test_check_connection(self):
        """Тест проверки соединения с OpenAI"""
        service = OpenAIService()
        
        with patch('services.openai_service.AsyncOpenAI') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            mock_instance.models.list.return_value = MagicMock()
            
            result = await service.check_connection()
            
            assert result is True


class TestFallbackService:
    """Тесты для улучшенного fallback сервиса"""
    
    @pytest.mark.asyncio
    async def test_get_fallback_response_price(self):
        """Тест ответа на вопрос о цене с фокусом на продажи"""
        service = FallbackService()
        
        result = await service.get_fallback_response("сколько стоит?")
        
        assert result is not None
        assert "стоимость" in result.lower() or "цена" in result.lower()
        assert ("консультация" in result.lower() or 
                "запишитесь" in result.lower() or 
                "звоните" in result.lower())
    
    @pytest.mark.asyncio
    async def test_get_fallback_response_duration(self):
        """Тест ответа на вопрос о длительности с фокусом на продажи"""
        service = FallbackService()
        
        result = await service.get_fallback_response("сколько длится?")
        
        assert result is not None
        assert ("час" in result.lower() or 
                "длительность" in result.lower() or
                "время" in result.lower())
        assert ("консультация" in result.lower() or 
                "запишитесь" in result.lower() or
                "фото" in result.lower())
    
    @pytest.mark.asyncio
    async def test_get_fallback_response_consultation(self):
        """Тест ответа на вопрос о консультации"""
        service = FallbackService()
        
        result = await service.get_fallback_response("как записаться на консультацию?")
        
        assert result is not None
        assert "бесплатную" in result.lower()
        assert ("консультация" in result.lower() or 
                "запишемся" in result.lower())
    
    @pytest.mark.asyncio
    async def test_get_fallback_response_unknown(self):
        """Тест ответа на неизвестный вопрос"""
        service = FallbackService()
        
        result = await service.get_fallback_response("какой сегодня день?")
        
        assert result is not None
        assert ("консультация" in result.lower() or 
                "хирург" in result.lower() or
                "звоните" in result.lower())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
