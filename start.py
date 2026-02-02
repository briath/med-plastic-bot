# Скрипт для инициализации и запуска проекта

import os
import sys
import subprocess
import asyncio
from pathlib import Path

def check_python_version():
    """Проверка версии Python"""
    if sys.version_info < (3, 11):
        print("❌ Требуется Python 3.11 или выше")
        sys.exit(1)
    print(f"✅ Python {sys.version}")

def check_env_file():
    """Проверка наличия .env файла"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ Файл .env не найден")
        print("Скопируйте .env.example в .env и настройте его")
        return False
    
    # Проверяем ключевые переменные
    with open(env_file) as f:
        content = f.read()
        if "your_telegram_bot_token_here" in content:
            print("❌ Настройте BOT_TOKEN в .env файле")
            return False
    
    print("✅ .env файл настроен")
    return True

def install_dependencies():
    """Установка зависимостей"""
    print("📦 Установка зависимостей...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=True)
        print("✅ Зависимости установлены")
        return True
    except subprocess.CalledProcessError:
        print("❌ Ошибка при установке зависимостей")
        return False

async def init_database():
    """Инициализация базы данных"""
    print("🗄️ Инициализация базы данных...")
    try:
        from models.base import create_db
        await create_db()
        print("✅ База данных инициализирована")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        return False

async def parse_services():
    """Парсинг услуг с сайта"""
    print("🌐 Парсинг услуг с сайта...")
    try:
        from services.parser import WebsiteParser
        from config.settings import settings
        from models.base import async_session_maker
        from models.repositories import ServiceRepository
        
        parser = WebsiteParser()
        service_data = await parser.parse_service_page(settings.clinic_website)
        
        async with async_session_maker() as session:
            repo = ServiceRepository(session)
            services = await repo.get_all()
            
            if not services and service_data:
                await repo.create(**service_data)
                print(f"✅ Услуга '{service_data.get('name')}' добавлена в БД")
            elif services:
                print("✅ Услуги уже есть в БД")
            else:
                print("⚠️ Не удалось получить данные с сайта, используются данные по умолчанию")
        
        return True
    except Exception as e:
        print(f"⚠️ Ошибка парсинга: {e}")
        return True  # Не критичная ошибка

def check_openai():
    """Проверка доступности OpenAI"""
    print("🤖 Проверка OpenAI...")
    try:
        import asyncio
        from services.openai_service import openai_service
        
        async def test_connection():
            return await openai_service.check_connection()
        
        result = asyncio.run(test_connection())
        if result:
            print("✅ OpenAI доступен")
            return True
        else:
            print("⚠️ OpenAI не отвечает, будет использован fallback режим")
            return False
    except Exception as e:
        print(f"⚠️ Ошибка проверки OpenAI: {e}")
        return False

def run_tests():
    """Запуск тестов"""
    print("🧪 Запуск тестов...")
    try:
        result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Тесты пройдены")
            return True
        else:
            print("⚠️ Некоторые тесты не пройдены:")
            print(result.stdout)
            return False
    except Exception as e:
        print(f"❌ Ошибка запуска тестов: {e}")
        return False

def start_bot():
    """Запуск бота"""
    print("🚀 Запуск Telegram бота...")
    try:
        subprocess.run([sys.executable, "main.py"])
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")

def start_admin():
    """Запуск админ-панели"""
    print("🎛️ Запуск админ-панели...")
    try:
        subprocess.run([sys.executable, "admin/main.py"])
    except KeyboardInterrupt:
        print("\n👋 Админ-панель остановлена")
    except Exception as e:
        print(f"❌ Ошибка запуска админ-панели: {e}")

def main():
    """Главная функция"""
    print("🏥 Med-Plastic Bot - Инициализация проекта\n")
    
    # Проверки
    check_python_version()
    
    if not check_env_file():
        return
    
    if not install_dependencies():
        return
    
    # Инициализация
    async def init():
        await init_database()
        await parse_services()
    
    asyncio.run(init())
    
    # Проверки (не блокирующие)
    check_openai()
    
    # Тесты (опционально)
    if "--test" in sys.argv:
        run_tests()
    
    print("\n🎉 Проект готов к запуску!")
    print("\nДоступные команды:")
    print("  python start.py              - Запуск бота")
    print("  python start.py admin        - Запуск админ-панели")
    print("  python start.py --test       - Запуск тестов")
    print("  docker-compose up -d         - Запуск в Docker")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "admin":
            start_admin()
        else:
            start_bot()

if __name__ == "__main__":
    main()
