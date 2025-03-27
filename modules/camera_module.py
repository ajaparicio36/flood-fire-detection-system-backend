import threading
import time
import cv2
import base64
import socketio
import logging
import os
from typing import Callable, Optional

# Set up basic logging configuration if not already configured
logging.basicConfig(level=logging.INFO)

class CameraModule:
    """
    Camera module for capturing video frames and sending them to an ML server for processing.
    
    This module captures frames from a camera (using OpenCV), converts them to base64,
    and sends them to a Socket.IO server for inference.
    """
    
    def __init__(self, 
                 ml_server_url: str = None,
                 camera_index: int = 0, 
                 capture_interval: float = 1.0,
                 resolution: tuple = (640, 480),  # Lower resolution for better performance
                 fps: int = 12,  # Added fps parameter
                 callback: Optional[Callable] = None,
                 max_reconnect_attempts: int = 5):
        """
        Initialize the camera module.
        
        Args:
            ml_server_url: URL of the ML inference server
            camera_index: Index of the camera to use (default: 0 for first camera)
            capture_interval: Interval between frame captures in seconds
            resolution: Resolution to capture frames at (width, height)
            fps: Maximum frames per second (default: 12)
            callback: Optional callback function to receive frame data
            max_reconnect_attempts: Maximum number of reconnection attempts
        """
        # Get ML server URL from parameter, environment, or default
        self.ml_server_url = ml_server_url or os.environ.get('ML_SERVER_URL') or 'http://localhost:5001'
        logging.info(f"ML Server URL: {self.ml_server_url}")
        
        self.camera_index = camera_index
        self.capture_interval = capture_interval
        self.resolution = resolution
        self.fps = fps
        self.callback = callback
        self.max_reconnect_attempts = max_reconnect_attempts
        
        # Initialize state variables
        self.is_running = False
        self.cap = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self.ml_server_connected = False
        
        # Initialize Socket.IO client for ML server connection
        self.sio = socketio.Client(reconnection=True, reconnection_attempts=max_reconnect_attempts)
        self._setup_socketio_events()

    def _setup_socketio_events(self):
        """Set up Socket.IO event handlers"""
        
        @self.sio.event
        def connect():
            logging.info("Connected to ML server")
            self.ml_server_connected = True
        
        @self.sio.event
        def connect_error(data):
            logging.error(f"Connection error to ML server: {data}")
            self.ml_server_connected = False
        
        @self.sio.event
        def disconnect():
            logging.info("Disconnected from ML server")
            self.ml_server_connected = False
        
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
    
        # Try to connect to ML server, but continue even if it fails
        self._connect_to_ml_server()
        
        # Main capture loop
        while not self._stop_event.is_set():
            try:
                # Capture frame
                ret, frame = self.cap.read()
                if not ret:
                    logging.warning("Failed to capture frame")
                    time.sleep(0.5)  # Brief pause before retrying
                    continue
                
                # Process frame locally if ML server is not connected
                if not self.ml_server_connected:
                    # If not connected to ML server, just pass the raw frame
                    if self.callback:
                        # Convert to base64 for consistent format
                        _, buffer = cv2.imencode('.jpg', frame)
                        base64_frame = base64.b64encode(buffer).decode('utf-8')
                        self.callback({
                            'frame': {'image': f'data:image/jpeg;base64,{base64_frame}'},
                            'timestamp': time.time(),
                            'ml_server_status': 'disconnected'
                        })
                    
                    # Try to reconnect periodically
                    if not hasattr(self, '_last_reconnect_attempt') or \
                       time.time() - self._last_reconnect_attempt > 30:  # Try every 30 seconds
                        self._reconnect_to_ml_server()
                else:
                    # Convert to base64
                    _, buffer = cv2.imencode('.jpg', frame)
                    base64_frame = base64.b64encode(buffer).decode('utf-8')
                    frame_data = f'data:image/jpeg;base64,{base64_frame}'
                    
                    # Send to ML server
                    try:
                        self.sio.emit('frame', frame_data)
                    except Exception as e:
                        logging.error(f"Error sending frame to ML server: {e}")
                        self.ml_server_connected = False
                
                # Wait for next capture
                time.sleep(self.capture_interval)
                
            except Exception as e:
                logging.error(f"Error in camera monitoring: {e}")
                time.sleep(1)  # Pause briefly before continuing
        
        self.cleanup()
    
    def _connect_to_ml_server(self):
        """Attempt to connect to ML server"""
        try:
            logging.info(f"Attempting to connect to ML server at {self.ml_server_url}")
            self.sio.connect(self.ml_server_url, wait_timeout=5)
            return True
        except Exception as e:
            logging.error(f"Failed to connect to ML server: {e}")
            self.ml_server_connected = False
            return False
    
    def _reconnect_to_ml_server(self):
        """Attempt to reconnect to ML server"""
        self._last_reconnect_attempt = time.time()
        if not self.sio.connected:
            return self._connect_to_ml_server()
        return True
    
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
                try:
                    self.sio.disconnect()
                except:
                    pass  # Ignore errors on disconnect