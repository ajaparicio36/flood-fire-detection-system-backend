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
        self.socketio = socketio
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.threshold = threshold
        self.ser = None
        self.is_running = False
    
    def find_arduino(self):
        """Find Arduino port automatically"""
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if any(id in p.hwid.lower() for id in ['arduino', '2341', '2a03', '1a86']):
                return p.device
            if any(name in p.description.lower() for name in ['arduino', 'uno', 'mega', 'ch340', 'ftdi']):
                return p.device
        if ports:
            return ports[0].device
        return None
    
    def connect(self):
        """Connect to Arduino"""
        if not self.port:
            self.port = self.find_arduino()
        if self.port:
            try:
                self.ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout
                )
                time.sleep(2)
                return True
            except serial.SerialException:
                return False
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
                return None
        return None
    
    def is_high_water_level(self, value):
        """Check if water level is high based on the threshold."""
        if value is None:
            return False
        return value > self.threshold

    def start_monitoring(self, interval=1.0):
        """
        Start monitoring the water level sensor and emit readings via websocket.

        Args:
            interval: Time between readings in seconds (default: 1.0)
        """
        if not self.connect():
            return
        
        self.is_running = True
    
        while self.is_running:
            reading = self.read_sensor()
        
            if reading is not None:
                high_water = self.is_high_water_level(reading)
            
                # Prepare data to emit
                data = {
                    'timestamp': time.time(),
                    'value': reading,
                    'high_water_level': high_water
                }
            
                # Emit reading via websocket
                emittedWaterLevelReading = self.socketio.emit('water_level_reading', data)
                print(f"Emitted water_level_reading: {emittedWaterLevelReading}")
            
                # If high water level is detected, also emit an alert
                if high_water:
                    alert_data = {
                        'timestamp': time.time(),
                        'message': 'High water level detected!'
                    }
                    emittedWaterLevelAlert =self.socketio.emit('water_level_alert', alert_data)
                    print(f"Emitted water_level_alert: {emittedWaterLevelAlert}")
                    
            time.sleep(interval)

    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.is_running = False
    
    def cleanup(self):
        """Clean up resources."""
        if self.ser:
            self.ser.close()
            self.ser = None
