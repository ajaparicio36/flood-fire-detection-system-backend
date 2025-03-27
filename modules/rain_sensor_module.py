import time
import RPi.GPIO as GPIO

class RainSensor:
    """
    Class to handle the FC37 YL-83 rain sensor connected to Raspberry Pi.
    Provides methods to initialize, read data, and return readings for external emission.
    """
    
    def __init__(self, digital_pin=12, analog_pin=None, threshold=500):
        """
        Initialize the rain sensor.
        
        Args:
            digital_pin: GPIO pin number for digital output (default: 12)
            analog_pin: GPIO pin number for analog output (if using ADC)
            threshold: Threshold value to detect rain (default: 500)
        """
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
    
    def get_sensor_data(self):
        """
        Read the sensor and return formatted data.
        
        Returns:
            dict: Data containing sensor readings and status
        """
        digital_reading = self.read_digital_sensor()
        rain_detected = self.is_rain_detected()
        
        # Debug prints
        print(f"Rain sensor digital reading: {digital_reading}")
        
        # Prepare data to return
        data = {
            'timestamp': time.time(),
            'value': digital_reading,
            'rain_detected': rain_detected
        }
        
        return data
    
    def start_monitoring(self, callback_fn, interval=1.0):
        """
        Start monitoring the rain sensor and call the callback with readings.
        
        Args:
            callback_fn: Function to call with sensor data
            interval: Time between readings in seconds (default: 1.0)
        """
        self.is_running = True
        
        while self.is_running:
            data = self.get_sensor_data()
            
            # Call the callback function with the data
            callback_fn(data)
            
            time.sleep(interval)
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.is_running = False
    
    def cleanup(self):
        """Clean up GPIO resources."""
        GPIO.cleanup(self.digital_pin)
