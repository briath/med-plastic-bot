import pytest
from unittest.mock import MagicMock, patch
from services.llm_service import LLMService, FallbackService


class TestLLMService:
    """Тесты для LLM сервиса"""
    
    @pytest.mark.asyncio
    async def test_generate_response_success(self):
        """Тест успешной генерации ответа"""
        service = LLMService()
        
        # Мокаем requests
        with patch('services.llm_service.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'response': 'Тестовый ответ от LLM'
            }
            mock_post.return_value = mock_response
            
            result = await service.generate_response(
                "Тестовый вопрос",
                {'service': {'name': 'Блефаропластика'}}
            )
            
            assert result == 'Тестовый ответ от LLM'
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_response_error(self):
        """Тест генерации ответа с ошибкой"""
        service = LLMService()
        
        # Мокаем requests с ошибкой
        with patch('services.llm_service.requests.post') as mock_post:
            mock_post.side_effect = Exception("Network error")
            
            result = await service.generate_response("Тестовый вопрос")
            
            assert result is None
    
    def test_build_prompt(self):
        """Тест построения промпта"""
        service = LLMService()
        
        prompt = service._build_prompt(
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
        
        assert "Анна" in prompt
        assert "Блефаропластика" in prompt
        assert "Какая цена?" in prompt
        assert "от 50 000 руб" in prompt
    
    @pytest.mark.asyncio
    async def test_check_connection(self):
        """Тест проверки соединения с Ollama"""
        service = LLMService()
        
        with patch('services.llm_service.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = await service.check_connection()
            
            assert result is True


class TestFallbackService:
    """Тесты для fallback сервиса"""
    
    @pytest.mark.asyncio
    async def test_get_fallback_response_price(self):
        """Тест ответа на вопрос о цене"""
        service = FallbackService()
        
        result = await service.get_fallback_response("сколько стоит?")
        
        assert result is not None
        assert "стоимость" in result.lower() or "цена" in result.lower()
        assert "руб" in result.lower()
    
    @pytest.mark.asyncio
    async def test_get_fallback_response_duration(self):
        """Тест ответа на вопрос о длительности"""
        service = FallbackService()
        
        result = await service.get_fallback_response("сколько длится?")
        
        assert result is not None
        assert "час" in result.lower() or "длительность" in result.lower()
    
    @pytest.mark.asyncio
    async def test_get_fallback_response_unknown(self):
        """Тест ответа на неизвестный вопрос"""
        service = FallbackService()
        
        result = await service.get_fallback_response("какой сегодня день?")
        
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
