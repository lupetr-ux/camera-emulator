FROM python:3.9-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements и устанавливаем Python пакеты
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем приложение
COPY app/ ./app/
COPY mediamtx.yml /mediamtx.yml

# Скрипт запуска
RUN echo '#!/bin/bash\npython /app/main.py &\n/mediamtx' > /app/start.sh && \
    chmod +x /app/start.sh

EXPOSE 5000 554 1935 8888 8889

CMD ["/app/start.sh"]
