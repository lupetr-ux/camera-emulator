#!/usr/bin/env python3
import os
import json
import time
import subprocess
from flask import Flask, render_template, jsonify, request, Response

app = Flask(__name__)
app.config['VIDEO_FOLDER'] = '/app/videos'
app.config['CONFIG_FOLDER'] = '/app/config'

cameras = {}
camera_counter = 0
config_file = '/app/config/cameras.json'
processes = {}

# Загружаем камеры
if os.path.exists(config_file):
    with open(config_file, 'r') as f:
        data = json.load(f)
        cameras = data.get('cameras', {})
        camera_counter = data.get('counter', 0)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def status():
    return jsonify({'status': 'ok'})

@app.route('/api/videos')
def list_videos():
    videos = []
    for file in os.listdir(app.config['VIDEO_FOLDER']):
        if file.endswith('.mp4'):
            videos.append({'name': file, 'size': '0MB'})
    return jsonify({'success': True, 'videos': videos})

@app.route('/api/cameras', methods=['GET'])
def get_cameras():
    camera_list = []
    for cam_id, cam in cameras.items():
        camera_list.append({
            'id': cam_id,
            'name': cam['name'],
            'status': 'running' if cam_id in processes else 'stopped',
            'video': os.path.basename(cam['video']),
            'username': 'admin'
        })
    return jsonify({'success': True, 'cameras': camera_list})

@app.route('/api/cameras', methods=['POST'])
def create_camera():
    global camera_counter
    data = request.json
    camera_counter += 1
    cam_id = str(camera_counter)
    
    cameras[cam_id] = {
        'id': cam_id,
        'name': data.get('name'),
        'video': data.get('video'),
        'username': 'admin',
        'password': 'admin123'
    }
    
    with open(config_file, 'w') as f:
        json.dump({'cameras': cameras, 'counter': camera_counter}, f)
    
    return jsonify({'success': True, 'camera_id': cam_id})

@app.route('/api/cameras/<cam_id>/start', methods=['POST'])
def start_camera(cam_id):
    if cam_id not in cameras:
        return jsonify({'success': False, 'error': 'Камера не найдена'})
    
    video = cameras[cam_id]['video']
    if not os.path.exists(video):
        return jsonify({'success': False, 'error': 'Видео не найдено'})
    
    # Останавливаем старый процесс
    if cam_id in processes:
        try:
            processes[cam_id].terminate()
            time.sleep(1)
        except:
            pass
    
    cmd = [
        'ffmpeg', '-re', '-stream_loop', '-1', '-i', video,
        '-an', '-c:v', 'libx264', '-preset', 'ultrafast',
        '-tune', 'zerolatency', '-f', 'rtsp', '-rtsp_transport', 'tcp',
        f'rtsp://localhost:554/camera{cam_id}'
    ]
    
    print(f"Запуск камеры {cam_id}")
    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    processes[cam_id] = process
    
    return jsonify({
        'success': True,
        'rtsp_url': f'rtsp://admin:admin123@192.168.30.130:554/camera{cam_id}'
    })

@app.route('/api/cameras/<cam_id>/stop', methods=['POST'])
def stop_camera(cam_id):
    if cam_id in processes:
        processes[cam_id].terminate()
        del processes[cam_id]
    return jsonify({'success': True})

@app.route('/api/cameras/<cam_id>', methods=['DELETE'])
def delete_camera(cam_id):
    if cam_id in processes:
        processes[cam_id].terminate()
        del processes[cam_id]
    if cam_id in cameras:
        del cameras[cam_id]
    with open(config_file, 'w') as f:
        json.dump({'cameras': cameras, 'counter': camera_counter}, f)
    return jsonify({'success': True})

# Добавим простое превью
@app.route('/api/cameras/<cam_id>/snapshot')
def camera_snapshot(cam_id):
    """Простое превью"""
    from PIL import Image, ImageDraw
    import io
    
    # Создаем простое изображение
    img = Image.new('RGB', (320, 180), color=(0, 100, 200))
    draw = ImageDraw.Draw(img)
    draw.text((10, 80), f"Camera {cam_id}", fill=(255, 255, 255))
    draw.text((10, 100), "RTSP OK", fill=(0, 255, 0))
    
    img_io = io.BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    
    return Response(img_io.getvalue(), mimetype='image/jpeg')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
