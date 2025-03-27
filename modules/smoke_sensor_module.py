import time
import RPi.GPIO as GPIO

class SmokeSensor:
    """
    Class to handle the MQ2 smoke/gas sensor connected to Raspberry Pi.
    Provides methods to initialize, read data without Socket.IO dependency.
    """
    
    def __init__(self, pin=11, threshold=300):
        """
        Initialize the smoke sensor.
        
        Args:
            pin: GPIO pin number (default: 11 which is GPIO 0)
            threshold: Threshold value to detect smoke (default: 300)
        """
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

    def start_monitoring(self, callback, interval=1.0):
        """
        Start monitoring the smoke sensor and send readings to callback.
        
        Args:
            callback: Function to call with sensor data
            interval: Time between readings in seconds (default: 1.0)
        """
        self.is_running = True
        
        while self.is_running:
            reading = self.read_sensor()
            smoke_detected = self.is_smoke_detected()

            # Debug prints
            print(f"Smoke sensor reading: {reading}")
            
            # Prepare data to send to callback
            data = {
                'timestamp': time.time(),
                'value': reading,
                'smoke_detected': smoke_detected
            }
            
            # Send data to callback function
            callback(data)

            time.sleep(interval)
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.is_running = False
    
    def cleanup(self):
        """Clean up GPIO resources."""
        GPIO.cleanup(self.pin)
