#!/bin/bash
echo "Восстановление конфигурации из бэкапа"

# Копируем файлы обратно
cp main.py /opt/camera-emulator/app/main.py
cp index.html /opt/camera-emulator/app/templates/index.html
cp video_stream.py /opt/camera-emulator/app/video_stream.py
cp docker-compose.yml /opt/camera-emulator/docker-compose.yml
cp Dockerfile /opt/camera-emulator/Dockerfile
[ -f cameras.json ] && cp cameras.json /opt/camera-emulator/config/cameras.json
[ -f mediamtx.yml ] && cp mediamtx.yml /opt/camera-emulator/mediamtx.yml

echo "Восстановление завершено"
echo "Для применения изменений выполните:"
echo "cd /opt/camera-emulator && docker-compose down && docker-compose up -d"
