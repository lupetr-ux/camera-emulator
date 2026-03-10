#!/usr/bin/env python3
import json
import subprocess
import time
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_cameras():
    config_file = '/app/config/cameras.json'
    
    if not os.path.exists(config_file):
        logger.info("Нет конфига с камерами")
        return
    
    try:
        with open(config_file, 'r') as f:
            data = json.load(f)
        
        cameras = data.get('cameras', {})
        
        for cam_id, cam in cameras.items():
            if cam.get('status') == 'running':
                video_path = cam.get('video')
                if os.path.exists(video_path):
                    stream_name = f"camera{cam_id}"
                    cmd = [
                        'ffmpeg',
                        '-re',
                        '-stream_loop', '-1',
                        '-i', video_path,
                        '-an',
                        '-c:v', 'libx264',
                        '-preset', 'ultrafast',
                        '-tune', 'zerolatency',
                        '-f', 'rtsp',
                        '-rtsp_transport', 'tcp',
                        f"rtsp://localhost:554/{stream_name}"
                    ]
                    
                    logger.info(f"Запуск камеры {cam_id}")
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(2)
                else:
                    logger.error(f"Видео не найдено для камеры {cam_id}: {video_path}")
    except Exception as e:
        logger.error(f"Ошибка запуска камер: {e}")

if __name__ == '__main__':
    time.sleep(5)  # Ждем запуска MediaMTX
    start_cameras()
