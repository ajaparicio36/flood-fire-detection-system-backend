import time
from flask_socketio import SocketIO
from flask import Flask

# filepath: D:/shs-rasp-pi-system/backend/modules/rain_sensor_module.py

import RPi.GPIO as GPIO

class RainSensor:
    """
    Class to handle the FC37 YL-83 rain sensor connected to Raspberry Pi.
    Provides methods to initialize, read data, and emit readings via websockets.
    """
    
    def __init__(self, socketio, digital_pin=12, analog_pin=None, threshold=500):
        """
        Initialize the rain sensor.
        
        Args:
            socketio: The SocketIO instance for emitting data
            digital_pin: GPIO pin number for digital output (default: 12)
            analog_pin: GPIO pin number for analog output (if using ADC)
            threshold: Threshold value to detect rain (default: 500)
        """
        self.socketio = socketio
        self.digital_pin = digital_pin
        self.analog_pin = analog_pin
        self.threshold = threshold
        self.is_running = False
        
        # Setup GPIO
        GPIO.setmode(GPIO.BOARD)  # Use physical pin numbering
        GPIO.setup(self.digital_pin, GPIO.IN)
    
    def read_digital_sensor(self):
        """Read the digital value from the rain sensor."""
        return GPIO.input(self.digital_pin)
    
    def is_rain_detected(self):
        """Check if rain is detected based on digital output."""
        # FC37 YL-83 outputs LOW when rain is detected
        return self.read_digital_sensor() == 0
    
    def start_monitoring(self, interval=1.0):
        """
        Start monitoring the rain sensor and emit readings via websocket.
        
        Args:
            interval: Time between readings in seconds (default: 1.0)
        """
        self.is_running = True
        
        while self.is_running:
            digital_reading = self.read_digital_sensor()
            rain_detected = self.is_rain_detected()
            
            # Debug prints
            print(f"Rain sensor digital reading: {digital_reading}")
            
            # Prepare data to emit
            data = {
                'timestamp': time.time(),
                'value': digital_reading,
                'rain_detected': rain_detected
            }
            
            # Emit reading via websocket
            emittedData = self.socketio.emit('rain_sensor_reading', data)
            print(f"Emitted rain_sensor_reading event: {emittedData}")
            
            # If rain is detected, also emit an alert
            if rain_detected:
                alert_message = 'Rain detected!'
                self.socketio.emit('rain_alert', {
                    'timestamp': time.time(),
                    'message': alert_message
                })
                print(f"Emitted rain_alert event: {alert_message}")
            
            time.sleep(interval)

    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.is_running = False
    
    def cleanup(self):
        """Clean up GPIO resources."""
        GPIO.cleanup(self.digital_pin)
