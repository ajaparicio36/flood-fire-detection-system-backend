import threading
import time
import cv2
import base64
import socketio
import logging
from typing import Callable, Optional

# filepath: d:\shs-rasp-pi-system\backend\modules\camera_module.py

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('camera_module')

class CameraModule:
    """
    Camera module for capturing video frames and sending them to an ML server for processing.
    
    This module captures frames from a camera (using OpenCV), converts them to base64,
    and sends them to a Socket.IO server for inference.
    """
    
    def __init__(self, 
                 ml_server_url: str = 'http://localhost:5001',
                 camera_index: int = 0, 
                 capture_interval: float = 1.0,
                 resolution: tuple = (640, 480),
                 callback: Optional[Callable] = None):
        """
        Initialize the camera module.
        
        Args:
            ml_server_url: URL of the ML inference server
            camera_index: Index of the camera to use (default: 0 for first camera)
            capture_interval: Interval between frame captures in seconds
            resolution: Resolution to capture frames at (width, height)
            callback: Optional callback function to receive frame data
        """
        self.camera_index = camera_index
        self.capture_interval = capture_interval
        self.resolution = resolution
        self.callback = callback
        self.ml_server_url = ml_server_url
        
        logger.info(f"Initializing CameraModule with ML server: {ml_server_url}, camera: {camera_index}")
        
        # Initialize state variables
        self.is_running = False
        self.cap = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        
        # Initialize Socket.IO client for ML server connection
        logger.debug("Creating SocketIO client")
        self.sio = socketio.Client(logger=True, engineio_logger=True)
        self._setup_socketio_events()
    
    def _setup_socketio_events(self):
        """Set up Socket.IO event handlers"""
        
        @self.sio.event
        def connect():
            logger.info(f"Connected to ML server at {self.ml_server_url}")
        
        @self.sio.event
        def connect_error(error):
            logger.error(f"Connection error to ML server: {error}")
        
        @self.sio.event
        def disconnect():
            logger.info("Disconnected from ML server")
        
        @self.sio.event
        def processed_frame(data):
            """Receive processed frame with detections from ML server"""
            logger.debug("Received processed frame from ML server")
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
        
        logger.info("Starting camera monitoring")
        
        with self._lock:
            if self.is_running:
                logger.warning("Camera module is already running")
                return
            
            # Connect to the camera
            try:
                logger.debug(f"Opening camera at index {self.camera_index}")
                self.cap = cv2.VideoCapture(self.camera_index)
                if not self.cap.isOpened():
                    logger.error(f"Failed to open camera at index {self.camera_index}")
                    return
                logger.info(f"Successfully opened camera at index {self.camera_index}")
            except Exception as e:
                logger.error(f"Error opening camera: {e}", exc_info=True)
                return
        
        # Set resolution
        logger.debug(f"Setting camera resolution to {self.resolution}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        
        # Reset stop event
        self._stop_event.clear()
        self.is_running = True
    
        # Connect to ML server
        try:
            logger.info(f"Attempting to connect to ML server at {self.ml_server_url}")
            self.sio.connect(self.ml_server_url)
            logger.info("SocketIO connect call completed")
        except Exception as e:
            logger.error(f"Failed to connect to ML server: {e}", exc_info=True)
            self.cleanup()
            return
        
        # Main capture loop
        logger.info("Starting main capture loop")
        frame_count = 0
        while not self._stop_event.is_set():
            try:
                # Capture frame
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning("Failed to capture frame")
                    time.sleep(0.5)  # Wait a bit before retrying
                    continue
                
                # Convert to base64
                frame_count += 1
                logger.debug(f"Processing frame {frame_count}")
                _, buffer = cv2.imencode('.jpg', frame)
                base64_frame = base64.b64encode(buffer).decode('utf-8')
                frame_data = f'data:image/jpeg;base64,{base64_frame}'
                
                # Send to ML server
                logger.debug(f"Sending frame {frame_count} to ML server")
                if self.sio.connected:
                    self.sio.emit('frame', frame_data)
                    logger.debug(f"Frame {frame_count} sent successfully")
                else:
                    logger.warning("Not connected to ML server, skipping frame")
                    try:
                        logger.info("Attempting to reconnect to ML server")
                        self.sio.connect(self.ml_server_url)
                    except Exception as e:
                        logger.error(f"Reconnection failed: {e}")
                
                # Wait for next capture
                time.sleep(self.capture_interval)
                
            except Exception as e:
                logger.error(f"Error in camera monitoring: {e}", exc_info=True)
                break
        
        logger.info("Exited main capture loop")
        self.cleanup()
    
    def stop_monitoring(self):
        """Stop the camera monitoring thread"""
        logger.info("Stopping camera monitoring")
        self._stop_event.set()
    
    def cleanup(self):
        """Release camera resources and disconnect from ML server"""
        logger.info("Cleaning up camera resources")
        with self._lock:
            self.is_running = False
            
            # Release camera
            if self.cap and self.cap.isOpened():
                logger.debug("Releasing camera")
                self.cap.release()
            
            # Disconnect from Socket.IO server
            if hasattr(self, 'sio') and self.sio.connected:
                logger.debug("Disconnecting from ML server")
                self.sio.disconnect()
        
        logger.info("Cleanup complete")