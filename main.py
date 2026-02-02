import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from utils.logger import setup_logging
from models.base import create_db, async_session_maker
from handlers.basic_handlers import router as basic_router
from handlers.consultation_handlers import router as consultation_router
from services.parser import WebsiteParser
from models.repositories import ServiceRepository


async def init_database():
    """Инициализация базы данных и заполнение начальными данными"""
    await create_db()
    
    async with async_session_maker() as session:
        # Проверяем, есть ли услуги в базе
        service_repo = ServiceRepository(session)
        services = await service_repo.get_all()
        
        if not services:
            # Если услуг нет, парсим сайт
            logging.info("No services found in database, parsing website...")
            parser = WebsiteParser()
            service_data = await parser.parse_service_page(settings.clinic_website)
            
            if service_data:
                await service_repo.create(**service_data)
                logging.info(f"Service '{service_data.get('name', 'Unknown')}' added to database")
            else:
                # Если парсинг не удался, добавляем базовую услугу
                default_service = {
                    'name': 'Блефаропластика верхних век',
                    'description': 'Пластика верхних век (блефаропластика) - хирургическая процедура по коррекции возрастных изменений верхних век.',
                    'indications': 'Нависание кожи верхних век, избыточная кожа, мешки под глазами, ухудшение поля зрения.',
                    'methods': 'Хирургическая блефаропластика, трансконъюнктивальная методика.',
                    'duration': '1-2 часа',
                    'recovery': '7-10 дней - отек и синяки, 2 недели - снятие швов, 1 месяц - возврат к обычной жизни.',
                    'price_range': 'от 50 000 до 120 000 рублей',
                    'source_url': settings.clinic_website
                }
                await service_repo.create(**default_service)
                logging.info("Default service added to database")


async def main():
    """Главная функция запуска бота"""
    # Настройка логирования
    logger = setup_logging()
    logger.info("Starting Med-Plastic bot...")
    
    # Инициализация базы данных
    await init_database()
    
    # Создание бота и диспетчера
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(
            parse_mode="Markdown"
        )
    )
    
    dp = Dispatcher(storage=MemoryStorage())
    
    # Подключаем middleware для работы с БД
    dp.update.middleware(DbSessionMiddleware())
    
    # Подключаем роутеры
    dp.include_router(basic_router)
    dp.include_router(consultation_router)
    
    # Запуск бота
    logger.info("Bot started successfully!")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


class DbSessionMiddleware:
    """Middleware для добавления сессии БД в обработчики"""
    
    async def __call__(self, handler, event, data):
        async with async_session_maker() as session:
            data["session"] = session
            return await handler(event, data)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Bot stopped with error: {e}")
