import threading
import time
import cv2
import base64
import socketio
import logging
from typing import Callable, Optional

# filepath: d:\shs-rasp-pi-system\backend\modules\camera_module.py

class CameraModule:
    """
    Camera module for capturing video frames and sending them to an ML server for processing.
    
    This module captures frames from a camera (using OpenCV), converts them to base64,
    and sends them to a Socket.IO server for inference.
    """
    
    def __init__(self, 
                 ml_server_url: str = 'http://192.168.1.24:5001',
                 camera_index: int = 0, 
                 capture_interval: float = 1.0,
                 resolution: tuple = (1280, 720),  # Changed to 720p
                 fps: int = 12,  # Added fps parameter
                 callback: Optional[Callable] = None):
        """
        Initialize the camera module.
        
        Args:
            ml_server_url: URL of the ML inference server
            camera_index: Index of the camera to use (default: 0 for first camera)
            capture_interval: Interval between frame captures in seconds
            resolution: Resolution to capture frames at (width, height)
            fps: Maximum frames per second (default: 12)
            callback: Optional callback function to receive frame data
        """
        self.camera_index = camera_index
        self.capture_interval = capture_interval
        self.resolution = resolution
        self.fps = fps  # Store the fps setting
        self.callback = callback
        self.ml_server_url = ml_server_url
        
        # Initialize state variables
        self.is_running = False
        self.cap = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        
        # Initialize Socket.IO client for ML server connection
        self.sio = socketio.Client()
        self._setup_socketio_events()

    
    def _setup_socketio_events(self):
        """Set up Socket.IO event handlers"""
        
        @self.sio.event
        def connect():
            logging.info("Connected to ML server")
        
        @self.sio.event
        def disconnect():
            logging.info("Disconnected from ML server")
        
        @self.sio.event
        def processed_frame(data):
            """Receive processed frame with detections from ML server"""
            if self.callback:
                # Forward the processed data to the callback
                self.callback({
                    'frame': data,
                    'timestamp': time.time()
                })
    
    def start_monitoring(self, callback: Optional[Callable] = None):
        """
        Start capturing frames from the camera and sending them to the ML server.
        
        Args:
            callback: Optional callback function to receive frame data
                      (can be set here or in constructor)
        """
        if callback:
            self.callback = callback
        
        with self._lock:
            if self.is_running:
                logging.warning("Camera module is already running")
                return
            
            # Connect to the camera
            try:
                self.cap = cv2.VideoCapture(self.camera_index)
                if not self.cap.isOpened():
                    logging.error(f"Failed to open camera at index {self.camera_index}")
                    return
            except Exception as e:
                logging.error(f"Error opening camera: {e}")
                return
        
        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        
        # Reset stop event
        self._stop_event.clear()
        self.is_running = True
    
        # Connect to ML server
        try:
            self.sio.connect(self.ml_server_url)
        except Exception as e:
            logging.error(f"Failed to connect to ML server: {e}")
            self.cleanup()
            return
        
        # Main capture loop
        while not self._stop_event.is_set():
            try:
                # Capture frame
                ret, frame = self.cap.read()
                if not ret:
                    logging.warning("Failed to capture frame")
                    continue
                
                # Convert to base64
                _, buffer = cv2.imencode('.jpg', frame)
                base64_frame = base64.b64encode(buffer).decode('utf-8')
                frame_data = f'data:image/jpeg;base64,{base64_frame}'
                
                # Send to ML server
                self.sio.emit('frame', frame_data)
                
                # Wait for next capture
                time.sleep(self.capture_interval)
                
            except Exception as e:
                logging.error(f"Error in camera monitoring: {e}")
                break
        
        self.cleanup()
    
    def stop_monitoring(self):
        """Stop the camera monitoring thread"""
        self._stop_event.set()
        logging.info("Camera monitoring stopped")
    
    def cleanup(self):
        """Release camera resources and disconnect from ML server"""
        with self._lock:
            self.is_running = False
            
            # Release camera
            if self.cap and self.cap.isOpened():
                self.cap.release()
            
            # Disconnect from Socket.IO server
            if self.sio.connected:
                self.sio.disconnect()