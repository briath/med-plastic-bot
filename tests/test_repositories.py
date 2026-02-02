import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from models.repositories import ServiceRepository, UserRepository
from models.database import Service, User
from services.parser import WebsiteParser


@pytest.fixture
async def session():
    """Фикстура для тестовой сессии БД"""
    # Здесь можно создать тестовую сессию
    # Для простоты используем mock
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def service_repo(session):
    """Фикстура для репозитория услуг"""
    return ServiceRepository(session)


@pytest.fixture
def user_repo(session):
    """Фикстура для репозитория пользователей"""
    return UserRepository(session)


class TestServiceRepository:
    """Тесты для репозитория услуг"""
    
    @pytest.mark.asyncio
    async def test_create_service(self, service_repo):
        """Тест создания услуги"""
        # Мокаем результат
        mock_service = Service(
            id=1,
            name="Тестовая услуга",
            description="Описание",
            price_range="от 10000 руб"
        )
        
        service_repo.session.add = MagicMock()
        service_repo.session.commit = AsyncMock()
        service_repo.session.refresh = AsyncMock()
        
        # Вызываем метод
        result = await service_repo.create(
            name="Тестовая услуга",
            description="Описание",
            price_range="от 10000 руб"
        )
        
        # Проверяем, что методы были вызваны
        service_repo.session.add.assert_called_once()
        service_repo.session.commit.assert_called_once()
        service_repo.session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_all_services(self, service_repo):
        """Тест получения всех услуг"""
        # Мокаем результат
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        
        service_repo.session.execute = AsyncMock(return_value=mock_result)
        
        # Вызываем метод
        result = await service_repo.get_all()
        
        # Проверяем
        assert isinstance(result, list)
        service_repo.session.execute.assert_called_once()


class TestUserRepository:
    """Тесты для репозитория пользователей"""
    
    @pytest.mark.asyncio
    async def test_get_by_telegram_id(self, user_repo):
        """Тест поиска пользователя по Telegram ID"""
        # Мокаем результат
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        
        user_repo.session.execute = AsyncMock(return_value=mock_result)
        
        # Вызываем метод
        result = await user_repo.get_by_telegram_id(12345)
        
        # Проверяем
        assert result is None
        user_repo.session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user(self, user_repo):
        """Тест создания пользователя"""
        # Мокаем результат
        mock_user = User(
            id=1,
            telegram_id=12345,
            first_name="Тест"
        )
        
        user_repo.session.add = MagicMock()
        user_repo.session.commit = AsyncMock()
        user_repo.session.refresh = AsyncMock(return_value=mock_user)
        
        # Вызываем метод
        result = await user_repo.create(
            telegram_id=12345,
            first_name="Тест"
        )
        
        # Проверяем
        user_repo.session.add.assert_called_once()
        user_repo.session.commit.assert_called_once()
        user_repo.session.refresh.assert_called_once()


class TestWebsiteParser:
    """Тесты для парсера сайта"""
    
    @pytest.mark.asyncio
    async def test_parse_service_page_success(self):
        """Тест успешного парсинга страницы"""
        parser = WebsiteParser()
        
        # Мокаем requests
        import requests
        original_get = requests.Session.get
        
        def mock_get(self, url, timeout=None):
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.encoding = 'utf-8'
            mock_response.text = """
            <html>
                <h1>Блефаропластика верхних век</h1>
                <p>Описание услуги</p>
                <div class="price">от 50 000 рублей</div>
            </html>
            """
            return mock_response
        
        requests.Session.get = mock_get
        
        try:
            result = await parser.parse_service_page("http://example.com")
            
            # Проверяем результат
            assert "name" in result
            assert "Блефаропластика" in result.get("name", "")
            
        finally:
            # Восстанавливаем оригинальный метод
            requests.Session.get = original_get
    
    @pytest.mark.asyncio
    async def test_parse_service_page_error(self):
        """Тест парсинга с ошибкой"""
        parser = WebsiteParser()
        
        # Мокаем requests с исключением
        import requests
        original_get = requests.Session.get
        
        def mock_get_error(self, url, timeout=None):
            raise requests.exceptions.RequestException("Network error")
        
        requests.Session.get = mock_get_error
        
        try:
            result = await parser.parse_service_page("http://example.com")
            
            # Проверяем, что при ошибке возвращается пустой dict
            assert result == {}
            
        finally:
            # Восстанавливаем оригинальный метод
            requests.Session.get = original_get


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
