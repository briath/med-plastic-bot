import logging
import sys
from config.settings import settings


def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("bot.log", encoding="utf-8"),
        ],
    )
    
    # Устанавливаем уровень для aiogram
    logging.getLogger("aiogram").setLevel(logging.INFO)
    
    return logging.getLogger(__name__)
