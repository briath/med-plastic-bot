import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str = Field(..., env="BOT_TOKEN")
    database_url: str = Field(default="sqlite+aiosqlite:///./med_plastic_bot.db", env="DATABASE_URL")
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    openai_base_url: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL")
    
    # Legacy Ollama settings (for backward compatibility)
    ollama_host: str = Field(default="http://localhost:11434", env="OLLAMA_HOST")
    ollama_model: str = Field(default="mistral:7b", env="OLLAMA_MODEL")
    
    admin_telegram_id: Optional[int] = Field(default=None, env="ADMIN_TELEGRAM_ID")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    clinic_name: str = Field(default="Мед-Пластик", env="CLINIC_NAME")
    clinic_phone: str = Field(default="+74951234567", env="CLINIC_PHONE")
    clinic_email: str = Field(default="info@med-plastic.ru", env="CLINIC_EMAIL")
    clinic_website: str = Field(default="https://med-plastic.ru/plastika-verhnih-vek/", env="CLINIC_WEBSITE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
