FROM python:3.12-slim

WORKDIR /app

# Копируем файлы с зависимостями (для кэширования)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

# Команда запуска
CMD ["python", "bot.py"]
