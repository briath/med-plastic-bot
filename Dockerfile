FROM python:3.8-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл с зависимостями
COPY pyproject.toml ./

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -e .

# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Копируем исходный код
COPY --chown=app:app . .

# Создаем директорию для данных с правильными правами
RUN mkdir -p /app/data && chown -R app:app /app/data

# Открываем порт для админ-панели
EXPOSE 8000

# Команда запуска
CMD ["python", "main.py"]
