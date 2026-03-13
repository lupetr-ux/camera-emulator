#!/bin/bash
echo "============================================"
echo "Восстановление ПОЛНОЙ РАБОЧЕЙ версии эмулятора"
echo "============================================"

# Копируем файлы обратно
cp main.py /opt/camera-emulator/app/main.py
cp video_stream.py /opt/camera-emulator/app/video_stream.py
cp index.html /opt/camera-emulator/app/templates/index.html
cp docker-compose.yml /opt/camera-emulator/docker-compose.yml
cp Dockerfile /opt/camera-emulator/Dockerfile
cp mediamtx.yml /opt/camera-emulator/mediamtx.yml
[ -f cameras.json ] && cp cameras.json /opt/camera-emulator/config/cameras.json

echo "✅ Файлы восстановлены"
echo ""
echo "Для запуска выполните:"
echo "cd /opt/camera-emulator"
echo "docker-compose down -v"
echo "docker-compose build --no-cache"
echo "docker-compose up -d"
echo ""
echo "После запуска откройте браузер и нажмите Ctrl+F5"
