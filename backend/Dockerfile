# Dockerfile в корне вашего Django-проекта (там, где manage.py)
FROM python:3.9-slim

WORKDIR /app

# Устанавливаем зависимости для сборки psycopg2 (PostgreSQL) и netcat
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл с зависимостями и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем всю вашу директорию приложения в /app
COPY . .

# Делаем entrypoint исполняемым и устанавливаем его
RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]