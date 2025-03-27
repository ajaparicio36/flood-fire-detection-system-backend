import os
import time
import threading
from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
from modules.water_level_sensor import WaterLevelSensor
from modules.rain_sensor_module import RainSensor
from modules.smoke_sensor_module import SmokeSensor

# filepath: D:/shs-rasp-pi-system/backend/main.py

# Import sensor modules

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for the Flask app
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize SocketIO with CORS allowed
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize sensors
water_sensor = WaterLevelSensor(socketio)
rain_sensor = RainSensor(socketio)
smoke_sensor = SmokeSensor(socketio)

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
    # Water level sensor
    water_thread = threading.Thread(target=water_sensor.start_monitoring)
    water_thread.daemon = True
    water_thread.start()
    sensor_threads['water_level'] = water_thread
    
    # Rain sensor
    rain_thread = threading.Thread(target=rain_sensor.start_monitoring)
    rain_thread.daemon = True
    rain_thread.start()
    sensor_threads['rain'] = rain_thread
    
    # Smoke sensor
    smoke_thread = threading.Thread(target=smoke_sensor.start_monitoring)
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