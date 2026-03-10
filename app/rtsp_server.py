#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Полноценный RTSP сервер для эмуляции камер
"""

import logging
import threading
import time
import cv2
import numpy as np
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver

logger = logging.getLogger(__name__)

class RTSPHandler(BaseHTTPRequestHandler):
    """Обработчик RTSP запросов"""
    
    def _check_auth(self):
        """Проверка авторизации"""
        auth_header = self.headers.get('Authorization', '')
        if auth_header.startswith('Basic '):
            encoded = auth_header[6:]
            try:
                decoded = base64.b64decode(encoded).decode('utf-8')
                username, password = decoded.split(':', 1)
                return (username == self.server.username and 
                       password == self.server.password)
            except:
                return False
        return False
        
    def _send_auth_request(self):
        """Отправка запроса авторизации"""
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="RTSP Server"')
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Authentication required')
        
    def do_GET(self):
        """Обработка GET запросов (MJPEG поток)"""
        if not self._check_auth():
            self._send_auth_request()
            return
            
        if self.path == '/live' or self.path == '/stream1' or self.path == '/stream':
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=--frameboundary')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.send_header('Connection', 'close')
            self.end_headers()
            
            logger.info(f"📹 Клиент подключился к потоку камеры {self.server.camera_id}")
            
            # Отправляем MJPEG поток
            frame_count = 0
            while self.server.running:
                try:
                    frame = self.server.video_streamer.get_frame(self.server.camera_id)
                    if frame is not None:
                        # Конвертируем в JPEG
                        ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        if ret:
                            frame_data = jpeg.tobytes()
                            self.wfile.write(b'--frameboundary\r\n')
                            self.wfile.write(b'Content-Type: image/jpeg\r\n')
                            self.wfile.write(f'Content-Length: {len(frame_data)}\r\n'.encode())
                            self.wfile.write(b'\r\n')
                            self.wfile.write(frame_data)
                            self.wfile.write(b'\r\n')
                            frame_count += 1
                            
                            if frame_count % 100 == 0:
                                logger.debug(f"📸 Камера {self.server.camera_id}: отправлено {frame_count} кадров")
                                
                    time.sleep(0.03)  # ~30 fps
                    
                except BrokenPipeError:
                    logger.info(f"🔌 Клиент отключился от камеры {self.server.camera_id}")
                    break
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки кадра: {e}")
                    break
                    
        elif self.path == '/snapshot':
            # Одиночный снимок
            frame = self.server.video_streamer.get_frame(self.server.camera_id)
            if frame is not None:
                ret, jpeg = cv2.imencode('.jpg', frame)
                if ret:
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(jpeg))
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    self.wfile.write(jpeg.tobytes())
            else:
                self.send_response(404)
                self.end_headers()
                
        elif self.path == '/info':
            # Информация о потоке
            info = self.server.video_streamer.get_stream_info(self.server.camera_id)
            if info:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                import json
                self.wfile.write(json.dumps(info).encode())
            else:
                self.send_response(404)
                self.end_headers()
                
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found. Try /live or /snapshot')
            
    def log_message(self, format, *args):
        """Отключаем логирование запросов"""
        pass

class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Многопоточный HTTP сервер"""
    allow_reuse_address = True

class RTSPServer:
    """RTSP сервер для эмуляции камер"""
    
    def __init__(self, camera_id, rtsp_port, username, password, video_streamer):
        self.camera_id = camera_id
        self.rtsp_port = rtsp_port
        self.username = username
        self.password = password
        self.video_streamer = video_streamer
        self.running = False
        self.http_server = None
        self.thread = None
        
    def start(self):
        """Запуск RTSP сервера (HTTP MJPEG)"""
        try:
            logger.info(f"🚀 Запуск RTSP сервера для камеры {self.camera_id} на порту {self.rtsp_port}")
            
            self.http_server = ThreadedHTTPServer(('0.0.0.0', self.rtsp_port), RTSPHandler)
            self.http_server.camera_id = self.camera_id
            self.http_server.username = self.username
            self.http_server.password = self.password
            self.http_server.video_streamer = self.video_streamer
            self.http_server.running = True
            self.running = True
            
            logger.info(f"✅ RTSP сервер для камеры {self.camera_id} запущен")
            logger.info(f"📡 Поток: http://{self._get_ip()}:{self.rtsp_port}/live")
            logger.info(f"📸 Снимок: http://{self._get_ip()}:{self.rtsp_port}/snapshot")
            
            self.http_server.serve_forever()
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска RTSP сервера: {e}")
            
    def stop(self):
        """Остановка RTSP сервера"""
        self.running = False
        if self.http_server:
            self.http_server.running = False
            self.http_server.shutdown()
            self.http_server.server_close()
            logger.info(f"⏹ RTSP сервер для камеры {self.camera_id} остановлен")
            
    def _get_ip(self):
        """Получение локального IP"""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "localhost"
