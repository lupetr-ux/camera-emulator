# 📹 IP Camera Emulator

Эмулятор IP-камер для тестирования NVR и систем видеонаблюдения.

## 🚀 Возможности

- ✅ RTSP потоки из видеофайлов
- ✅ Веб-интерфейс для управления
- ✅ Превью камер в реальном времени
- ✅ Загрузка видео (MP4, AVI, MOV)
- ✅ Автозапуск камер
- ✅ Docker контейнер

## 📦 Быстрый старт

git clone https://github.com/lupetr-ux/camera-emulator.git
cd camera-emulator
mkdir -p videos config
docker-compose up -d

## 🎮 Использование

1. Открой http://IP:5001
2. Загрузи видеофайлы
3. Создай камеру
4. Нажми "Старт"

## 🔌 RTSP URL

rtsp://admin:admin123@IP:554/cameraID

## ⚙️ Порты

- 5001 - веб-интерфейс
- 554 - RTSP
- 1935 - RTMP
- 8880-8881 - HLS/WebRTC
