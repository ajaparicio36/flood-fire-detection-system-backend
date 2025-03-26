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
