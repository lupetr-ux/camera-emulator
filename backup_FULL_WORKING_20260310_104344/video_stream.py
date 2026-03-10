#!/usr/bin/env python3
import cv2
import threading
import time
import logging

logger = logging.getLogger(__name__)

class VideoStreamer:
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.streams = {}
        self.running = False
        self.thread = None
        
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._stream_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info("VideoStreamer started")
        return True
        
    def stop(self):
        self.running = False
        for camera_id in list(self.streams.keys()):
            self.stop_stream(camera_id)
            
    def start_stream(self, camera_id, video_path, fps=30):
        try:
            if camera_id in self.streams:
                self.stop_stream(camera_id)
                
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Failed to open video: {video_path}")
                return False
                
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            if video_fps <= 0:
                video_fps = fps
                
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Read first frame to test
            ret, test_frame = cap.read()
            if not ret or test_frame is None:
                logger.error("Could not read first frame")
                return False
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            self.streams[camera_id] = {
                'cap': cap,
                'fps': video_fps,
                'width': width,
                'height': height,
                'total_frames': total_frames,
                'running': True,
                'last_frame': None,
                'frame_count': 0,
                'start_time': time.time()
            }
            
            logger.info(f"Stream {camera_id} started: {width}x{height} @ {video_fps}fps")
            return True
            
        except Exception as e:
            logger.error(f"Error starting stream: {e}")
            return False
            
    def stop_stream(self, camera_id):
        if camera_id in self.streams:
            if 'cap' in self.streams[camera_id]:
                self.streams[camera_id]['cap'].release()
            del self.streams[camera_id]
            logger.info(f"Stream {camera_id} stopped")
            
    def get_frame(self, camera_id):
        if camera_id not in self.streams:
            return None
        return self.streams[camera_id].get('last_frame')
        
    def get_stream_info(self, camera_id):
        if camera_id not in self.streams:
            return None
        stream = self.streams[camera_id]
        uptime = time.time() - stream['start_time']
        return {
            'width': stream['width'],
            'height': stream['height'],
            'fps': stream['fps'],
            'frames_sent': stream['frame_count'],
            'uptime': int(uptime)
        }
        
    def _stream_loop(self):
        frame_times = {}
        while self.running:
            try:
                current_time = time.time()
                for camera_id, stream in list(self.streams.items()):
                    if not stream['running']:
                        continue
                        
                    last_frame_time = frame_times.get(camera_id, 0)
                    if current_time - last_frame_time < 1.0 / stream['fps']:
                        continue
                        
                    ret, frame = stream['cap'].read()
                    if not ret:
                        stream['cap'].set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = stream['cap'].read()
                        
                    if ret and frame is not None:
                        stream['last_frame'] = frame.copy()
                        stream['frame_count'] += 1
                        frame_times[camera_id] = current_time
                        
                time.sleep(0.001)
            except Exception as e:
                logger.error(f"Error in stream loop: {e}")
                time.sleep(0.1)
