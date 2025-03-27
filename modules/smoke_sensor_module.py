import time
from flask_socketio import SocketIO
from flask import Flask
from flask_socketio import SocketIO

import RPi.GPIO as GPIO

class SmokeSensor:
    """
    Class to handle the MQ2 smoke/gas sensor connected to Raspberry Pi.
    Provides methods to initialize, read data, and emit readings via websockets.
    """
    
    def __init__(self, socketio, pin=11, threshold=300):
        """
        Initialize the smoke sensor.
        
        Args:
            socketio: The SocketIO instance for emitting data
            pin: GPIO pin number (default: 11 which is GPIO 0)
            threshold: Threshold value to detect smoke (default: 300)
        """
        self.socketio = socketio
        self.pin = pin
        self.threshold = threshold
        self.is_running = False
        
        # Setup GPIO with pull-down resistor to reduce noise
        GPIO.setmode(GPIO.BOARD)  # Use physical pin numbering
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
    def read_sensor(self):
        """Read the current value from the smoke sensor."""
        return GPIO.input(self.pin)
    
    def is_smoke_detected(self):
        """Check if smoke is detected based on the threshold."""
        value = self.read_sensor()
        return value == GPIO.LOW  # MQ2 outputs LOW when gas detected

    def start_monitoring(self, interval=1.0):
        """
        Start monitoring the smoke sensor and emit readings via websocket.
        
        Args:
            interval: Time between readings in seconds (default: 1.0)
        """
        self.is_running = True
        
        while self.is_running:
            reading = self.read_sensor()
            smoke_detected = self.is_smoke_detected()
            
            # Prepare data to emit
            data = {
                'timestamp': time.time(),
                'value': reading,
                'smoke_detected': smoke_detected
            }
            
            # Emit reading via websocket
            emittedSmokeReading = self.socketio.emit('smoke_sensor_reading', data)
            print(f"Emitted smoke_sensor_reading: {emittedSmokeReading}")
            # If smoke is detected, also emit an alert
            if smoke_detected:
                alert_data = {
                    'timestamp': time.time(),
                    'message': 'Smoke or gas detected!'
                }
                emittedSmokeAlert = self.socketio.emit('smoke_alert', alert_data)
                print(f"Emitted smoke_alert: {emittedSmokeAlert}")
                
            time.sleep(interval)
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.is_running = False
    
    def cleanup(self):
        """Clean up GPIO resources."""
        GPIO.cleanup(self.pin)
