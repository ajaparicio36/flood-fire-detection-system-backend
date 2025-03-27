import time
import threading
from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
from modules.water_level_sensor import WaterLevelSensor
from modules.rain_sensor_module import RainSensor
from modules.smoke_sensor_module import SmokeSensor

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for the Flask app
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize SocketIO with CORS allowed
# Initialize SocketIO with CORS allowed
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
# Define sensor callbacks
def water_level_callback(data):
    socketio.emit('water_level_reading', data)
    # Send alert if water level is high
    if data.get('high_water_level'):
        socketio.emit('water_level_alert', {
            'message': f"HIGH WATER LEVEL DETECTED: {data['value']}"
        })

def rain_sensor_callback(data):
    socketio.emit('rain_sensor_reading', data)
    # Send alert if rain is detected
    if data.get('rain_detected'):
        socketio.emit('rain_alert', {
            'message': f"RAINFALL DETECTED: {data['value']}"
        })

def smoke_sensor_callback(data):
    socketio.emit('smoke_sensor_reading', data)
    # Send alert if smoke is detected
    if data.get('smoke_detected'):
        socketio.emit('smoke_alert', {
            'message': f"SMOKE/GAS DETECTED: {data['value']}"
        })

# Initialize sensors with callbacks
water_sensor = WaterLevelSensor(callback=water_level_callback)
rain_sensor = RainSensor()
smoke_sensor = SmokeSensor()

# Dictionary to store sensor threads
sensor_threads = {}

# API routes
@app.route('/')
def index():
    return jsonify({"status": "Smart Home System API running"})

@app.route('/api/status')
def status():
    return jsonify({
        "status": "online",
        "sensors": {
            "water_level": water_sensor.is_running,
            "rain": rain_sensor.is_running,
            "smoke": smoke_sensor.is_running
        }
    })

# Start sensor monitoring in separate threads
def start_sensors():
    """
    Initialize and start monitoring threads for all sensors in the system.
    This function creates separate daemon threads for each sensor (water level, rain, and smoke),
    and registers them in the global sensor_threads dictionary for tracking. Sensor readings and alerts
    are emitted to the connected clients via Socket.IO:
    @Events Emitted:
    - water_level_reading: Regular water level sensor readings {value: int}
    - water_level_alert: Water level alerts {message: str}
    - rain_sensor_reading: Regular rain sensor readings {value: int, rain_detected: bool}
    - rain_alert: Rain detection alerts {message: str}
    - smoke_sensor_reading: Regular smoke sensor readings {value: int, smoke_detected: bool}
    - smoke_alert: Smoke detection alerts {message: str}
    Each sensor runs in its own thread to prevent blocking the main application thread.
    All threads are set as daemon threads so they will terminate when the main program exits.
    """
    # Water level sensor
    water_thread = threading.Thread(target=water_sensor.start_monitoring)
    water_thread.daemon = True
    water_thread.start()
    sensor_threads['water_level'] = water_thread
    
    # Rain sensor
    rain_thread = threading.Thread(target=lambda: rain_sensor.start_monitoring(rain_sensor_callback))
    rain_thread.daemon = True
    rain_thread.start()
    sensor_threads['rain'] = rain_thread
    
    # Smoke sensor
    smoke_thread = threading.Thread(target=lambda: smoke_sensor.start_monitoring(smoke_sensor_callback))
    smoke_thread.daemon = True
    smoke_thread.start()
    sensor_threads['smoke'] = smoke_thread

# SocketIO events
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    socketio.emit('connection_status', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

# Cleanup function
def cleanup():
    water_sensor.stop_monitoring()
    rain_sensor.stop_monitoring()
    smoke_sensor.stop_monitoring()
    
    # Wait for threads to finish
    time.sleep(1)
    
    water_sensor.cleanup()
    rain_sensor.cleanup()
    smoke_sensor.cleanup()

if __name__ == "__main__":
    try:
        # Start sensor monitoring
        start_sensors()

        # Run the Flask app with SocketIO
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        cleanup()