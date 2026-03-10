#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Менеджер для управления RTSP сервером mediamtx
"""

import os
import subprocess
import logging
import signal
import time
import psutil

logger = logging.getLogger(__name__)

class RTSPServerManager:
    """Менеджер для запуска RTSP сервера через mediamtx"""
    
    def __init__(self):
        self.processes = {}  # camera_id -> process
        self.ffmpeg_processes = {}  # camera_id -> ffmpeg process
        
    def start_rtsp_stream(self, camera_id, input_file, rtsp_port, username, password):
        """Запуск RTSP потока через mediamtx + ffmpeg"""
        try:
            # Создаем конфиг для mediamtx если нужно (но проще использовать стандартный)
            
            # Запускаем ffmpeg для подачи видео в RTSP сервер
            # Используем UDP для локальной передачи
            ffmpeg_cmd = [
                'ffmpeg',
                '-re',  # Читаем в реальном времени
                '-stream_loop', '-1',  # Зацикливаем
                '-i', input_file,
                '-c', 'copy',  # Копируем без перекодирования
                '-f', 'rtsp',
                f'rtsp://localhost:8554/{camera_id}'
            ]
            
            # Запускаем ffmpeg процесс
            ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self.ffmpeg_processes[camera_id] = ffmpeg_process
            
            # Даем время на запуск
            time.sleep(2)
            
            # Проверяем что процесс запущен
            if ffmpeg_process.poll() is None:
                logger.info(f"RTSP поток для камеры {camera_id} запущен: rtsp://{username}:{password}@0.0.0.0:8554/{camera_id}")
                return True
            else:
                logger.error(f"Ошибка запуска ffmpeg для камеры {camera_id}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка запуска RTSP: {e}")
            return False
            
    def stop_rtsp_stream(self, camera_id):
        """Остановка RTSP потока"""
        try:
            # Останавливаем ffmpeg
            if camera_id in self.ffmpeg_processes:
                process = self.ffmpeg_processes[camera_id]
                
                # Пытаемся завершить процесс мягко
                process.terminate()
                
                # Ждем немного
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Если не завершился, убиваем принудительно
                    process.kill()
                
                del self.ffmpeg_processes[camera_id]
                logger.info(f"RTSP поток для камеры {camera_id} остановлен")
                
        except Exception as e:
            logger.error(f"Ошибка остановки RTSP: {e}")
            
    def stop_all(self):
        """Остановка всех потоков"""
        for camera_id in list(self.ffmpeg_processes.keys()):
            self.stop_rtsp_stream(camera_id)
