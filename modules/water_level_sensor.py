import serial
import serial.tools.list_ports
import time
import datetime
from typing import Optional
from flask_socketio import SocketIO

class WaterLevelSensor:
    """
    Class to handle the water level sensor connected to Arduino.
    Provides methods to initialize, read data, and emit readings via websockets.
    """
    
    def __init__(self, socketio: SocketIO, port: Optional[str] = None, baudrate: int = 9600, timeout: int = 1, threshold: int = 500):
        """
        Initialize water level sensor.
        
        Args:
            socketio: The SocketIO instance for emitting data
            port: COM port of Arduino. If None, will attempt to auto-detect
            baudrate: Baud rate for serial communication
            timeout: Serial read timeout in seconds
            threshold: Threshold value to detect high water level (default: 500)
        """
        self.socketio = socketio
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.threshold = threshold
        self.ser = None
        self.is_running = False
    
    def find_arduino(self):
        """Find Arduino port automatically"""
        # List all ports with details
        ports = list(serial.tools.list_ports.comports())
        
        # Print all available ports for debugging
        print("Available ports:")
        for i, p in enumerate(ports):
            print(f"{i}: {p.device} - {p.description} - {p.hwid}")
        
        # First try to find by known Arduino identifiers
        for p in ports:
            # Common Arduino identifiers
            if any(id in p.hwid.lower() for id in ['arduino', '2341', '2a03', '1a86']):
                return p.device
                
            # Some Arduinos show up with these in the description
            if any(name in p.description.lower() for name in ['arduino', 'uno', 'mega', 'ch340', 'ftdi']):
                return p.device
        
        # If no Arduino found but there are ports available, use the first one
        if ports:
            print("\nCouldn't automatically identify Arduino. Using first available port.")
            return ports[0].device
        
        return None
    
    def connect(self):
        """Connect to Arduino"""
        if not self.port:
            self.port = self.find_arduino()
            
        if self.port:
            print(f"Using Arduino port: {self.port}")
            
            try:
                self.ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout
                )
                
                # Wait for serial connection to establish
                time.sleep(2)
                return True
            except serial.SerialException as e:
                print(f"Error connecting to Arduino: {e}")
                return False
        else:
            print("Arduino not found. Make sure it's connected properly.")
            return False
    
    def read_sensor(self):
        """Read the current value from the water level sensor."""
        if not self.ser:
            return None
            
        if self.ser.in_waiting > 0:
            line = self.ser.readline().decode('utf-8').strip()
            try:
                value = int(line)
                return value
            except ValueError:
                print(f"Received invalid data: {line}")
                return None
        
        return None
    
    def is_high_water_level(self, value):
        """Check if water level is high based on the threshold."""
        if value is None:
            return False
        return value > self.threshold
    
    def read_sensor(self):
        """Read the current value from the water level sensor."""
        if not self.ser:
            print("Serial connection not established")
            return None
        
        if self.ser.in_waiting > 0:
            line = self.ser.readline().decode('utf-8').strip()
            print(f"Raw data received: '{line}'")
            try:
                value = int(line)
                print(f"Parsed water level value: {value}")
                return value
            except ValueError:
                print(f"Received invalid data: {line}")
                return None
        else:
            print("No data available from serial port")
    
        return None

    def start_monitoring(self, interval=1.0):
        """
        Start monitoring the water level sensor and emit readings via websocket.

        Args:
            interval: Time between readings in seconds (default: 1.0)
        """
        if not self.connect():
            print("Failed to connect to water level sensor")
            return
        
        self.is_running = True
        print(f"Water level monitoring started, interval: {interval}s")
    
        while self.is_running:
            reading = self.read_sensor()
        
            if reading is not None:
                high_water = self.is_high_water_level(reading)
                print(f"Reading: {reading}, High water: {high_water}, Threshold: {self.threshold}")
            
                # Prepare data to emit
                data = {
                    'timestamp': time.time(),
                    'value': reading,
                    'high_water_level': high_water
                }
            
                # Emit reading via websocket
                print(f"Emitting water_level_reading: {data}")
                self.socketio.emit('water_level_reading', data)
            
                # If high water level is detected, also emit an alert
                if high_water:
                    alert_data = {
                        'timestamp': time.time(),
                        'message': 'High water level detected!'
                    }
                    print(f"Emitting water_level_alert: {alert_data}")
                    self.socketio.emit('water_level_alert', alert_data)
            else:
                print("No valid reading obtained")
        
            print(f"Waiting {interval}s before next reading...")
            time.sleep(interval)

    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.is_running = False
    
    def cleanup(self):
        """Clean up resources."""
        if self.ser:
            self.ser.close()
            self.ser = None
            print("Serial connection closed")

# Example usage with Flask-SocketIO
if __name__ == "__main__":
    # This is just for testing/example purposes
    from flask import Flask
    from flask_socketio import SocketIO
    
    app = Flask(__name__)
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    water_sensor = WaterLevelSensor(socketio)
    
    @app.route('/')
    def index():
        return "Water Level Sensor Module Running"
    
    import threading
    sensor_thread = threading.Thread(target=water_sensor.start_monitoring)
    sensor_thread.daemon = True
    sensor_thread.start()
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)