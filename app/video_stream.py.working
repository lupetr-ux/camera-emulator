#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для работы с видео и RTSP потоками
"""

import cv2
import numpy as np
import threading
import time
import logging
import base64
from datetime import datetime

logger = logging.getLogger(__name__)

class VideoStreamer:
    """Класс для стриминга видео с зацикливанием"""
    
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.streams = {}  # camera_id -> stream object
        self.running = False
        self.thread = None
        
    def start(self):
        """Запуск менеджера стримов"""
        self.running = True
        self.thread = threading.Thread(target=self._stream_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info("✅ Видео менеджер запущен")
        return True
        
    def stop(self):
        """Остановка всех стримов"""
        self.running = False
        for camera_id in list(self.streams.keys()):
            self.stop_stream(camera_id)
        logger.info("⏹ Видео менеджер остановлен")
        
    def start_stream(self, camera_id, video_path, fps=30):
        """Запуск стрима для камеры"""
        try:
            if camera_id in self.streams:
                self.stop_stream(camera_id)
                
            logger.info(f"📹 Запуск стрима для камеры {camera_id}: {video_path}")
            
            # Проверяем существование файла
            import os
            if not os.path.exists(video_path):
                logger.error(f"❌ Видеофайл не найден: {video_path}")
                return False
                
            # Открываем видео
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"❌ Не удалось открыть видео {video_path}")
                return False
                
            # Получаем информацию о видео
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            if video_fps <= 0:
                video_fps = fps
                logger.warning(f"⚠️ Не удалось определить FPS, используем {fps}")
                
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if width <= 0 or height <= 0:
                width, height = 1920, 1080
                logger.warning(f"⚠️ Не удалось определить разрешение, используем {width}x{height}")
            
            # Создаем объект стрима
            self.streams[camera_id] = {
                'cap': cap,
                'fps': video_fps,
                'width': width,
                'height': height,
                'total_frames': total_frames,
                'current_frame': 0,
                'running': True,
                'last_frame': None,
                'frame_count': 0,
                'start_time': time.time(),
                'video_path': video_path
            }
            
            logger.info(f"✅ Стрим для камеры {camera_id} запущен: {width}x{height} @ {video_fps:.2f}fps, кадров: {total_frames}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска стрима: {e}")
            return False
            
    def stop_stream(self, camera_id):
        """Остановка стрима камеры"""
        if camera_id in self.streams:
            stream = self.streams[camera_id]
            if 'cap' in stream:
                stream['cap'].release()
            del self.streams[camera_id]
            logger.info(f"⏹ Стрим для камеры {camera_id} остановлен")
            
    def get_frame(self, camera_id):
        """Получение текущего кадра для камеры"""
        if camera_id not in self.streams:
            return None
            
        stream = self.streams[camera_id]
        return stream.get('last_frame')
        
    def get_stream_info(self, camera_id):
        """Получение информации о стриме"""
        if camera_id not in self.streams:
            return None
            
        stream = self.streams[camera_id]
        uptime = time.time() - stream['start_time']
        
        return {
            'width': stream['width'],
            'height': stream['height'],
            'fps': stream['fps'],
            'total_frames': stream['total_frames'],
            'frames_sent': stream['frame_count'],
            'uptime': int(uptime),
            'looping': True,
            'running': stream['running']
        }
        
    def _stream_loop(self):
        """Основной цикл обработки видео"""
        logger.info("🔄 Запуск цикла обработки видео")
        frame_times = {}
        
        while self.running:
            try:
                current_time = time.time()
                
                for camera_id, stream in list(self.streams.items()):
                    if not stream['running']:
                        continue
                        
                    # Контроль FPS
                    last_frame_time = frame_times.get(camera_id, 0)
                    if current_time - last_frame_time < 1.0 / stream['fps']:
                        continue
                        
                    # Читаем кадр
                    ret, frame = stream['cap'].read()
                    
                    if not ret:
                        # Зацикливаем видео
                        logger.debug(f"🔄 Зацикливание видео для камеры {camera_id}")
                        stream['cap'].set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = stream['cap'].read()
                        
                    if ret and frame is not None:
                        stream['last_frame'] = frame.copy()
                        stream['frame_count'] += 1
                        stream['current_frame'] = stream['frame_count'] % stream['total_frames']
                        frame_times[camera_id] = current_time
                        
                        # Отправляем кадр через WebSocket для превью (каждые 2 кадра для экономии)
                        if self.socketio and stream['frame_count'] % 2 == 0:
                            self._send_preview(camera_id, frame)
                            
                time.sleep(0.001)  # Небольшая задержка
                
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле обработки видео: {e}")
                time.sleep(0.1)
                
    def _send_preview(self, camera_id, frame):
        """Отправка превью через WebSocket"""
        try:
            # Уменьшаем размер для превью
            height, width = frame.shape[:2]
            if width > 320:
                scale = 320 / width
                new_width = 320
                new_height = int(height * scale)
                preview = cv2.resize(frame, (new_width, new_height))
            else:
                preview = frame
                
            # Конвертируем в JPEG и затем в base64
            ret, jpeg = cv2.imencode('.jpg', preview, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if ret:
                jpeg_base64 = base64.b64encode(jpeg).decode('utf-8')
                
                # Отправляем через SocketIO
                self.socketio.emit('frame', {
                    'camera_id': camera_id,
                    'image': jpeg_base64,
                    'timestamp': datetime.now().isoformat()
                }, namespace='/preview')
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки превью: {e}")
