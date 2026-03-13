#!/usr/bin/env python3
import os
import json
import time
import subprocess
from datetime import datetime
from flask import Flask, render_template, jsonify, request, Response
from video_stream import VideoStreamer

app = Flask(__name__)
app.config['VIDEO_FOLDER'] = '/app/videos'
app.config['CONFIG_FOLDER'] = '/app/config'

video_streamer = VideoStreamer()
video_streamer.start()

cameras = {}
camera_counter = 0
config_file = '/app/config/cameras.json'
processes = {}

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
            'username': 'admin',
            'stream_info': video_streamer.get_stream_info(cam_id)
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
    
    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    processes[cam_id] = process
    
    # Запускаем video_streamer для превью
    video_streamer.start_stream(cam_id, video, 30)
    
    return jsonify({
        'success': True,
        'rtsp_url': f'rtsp://admin:admin123@192.168.30.130:554/camera{cam_id}'
    })

@app.route('/api/cameras/<cam_id>/stop', methods=['POST'])
def stop_camera(cam_id):
    if cam_id in processes:
        processes[cam_id].terminate()
        del processes[cam_id]
    video_streamer.stop_stream(cam_id)
    return jsonify({'success': True})

@app.route('/api/cameras/<cam_id>', methods=['DELETE'])
def delete_camera(cam_id):
    if cam_id in processes:
        processes[cam_id].terminate()
        del processes[cam_id]
    video_streamer.stop_stream(cam_id)
    if cam_id in cameras:
        del cameras[cam_id]
    with open(config_file, 'w') as f:
        json.dump({'cameras': cameras, 'counter': camera_counter}, f)
    return jsonify({'success': True})

@app.route('/api/cameras/<cam_id>/snapshot')
def camera_snapshot(cam_id):
    """Реальное превью из видео"""
    try:
        frame = video_streamer.get_frame(cam_id)
        
        if frame is None:
            from PIL import Image, ImageDraw
            import io
            
            img = Image.new('RGB', (320, 180), color=(0, 100, 200))
            draw = ImageDraw.Draw(img)
            draw.text((10, 80), f"Camera {cam_id}", fill=(255, 255, 255))
            draw.text((10, 100), "No signal", fill=(255, 0, 0))
            
            img_io = io.BytesIO()
            img.save(img_io, 'JPEG')
            img_io.seek(0)
            return Response(img_io.getvalue(), mimetype='image/jpeg')
        
        import cv2
        ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            return "Error encoding frame", 500
            
        return Response(jpeg.tobytes(), mimetype='image/jpeg')
        
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
