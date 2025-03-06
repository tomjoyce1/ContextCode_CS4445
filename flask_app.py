from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import os
from flask_socketio import SocketIO, emit

# Set up database path without deleting
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'metrics.db')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

def aware_utcnow():
    return datetime.now(timezone.utc)

class CpuUsage(db.Model):
    __tablename__ = 'cpu_usage'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    cpu_usage = db.Column(db.Float, nullable=False)

class BatteryPercentage(db.Model):
    __tablename__ = 'battery_percentage'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    battery_percentage = db.Column(db.Float, nullable=False)

class IssLocation(db.Model):
    __tablename__ = 'iss_location'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    location = db.Column(db.String, nullable=False)

# Only create tables if they don't exist
with app.app_context():
    try:
        # db.drop_all()
        db.create_all()
        print('Checked database tables - created if not existing')
    except Exception as e:
        print(f"Error checking database tables: {e}")
        raise

latest_command = None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/metrics', methods=['POST'])
def receive_metrics():
    data = request.json
    device_id = data.get('device_id', 'unknown_device')  # Ensure this is consistent
    timestamp = datetime.strptime(data['timestamp'], '%Y-%m-%dT%H:%M:%S.%f')

    metrics = [
        CpuUsage(timestamp=timestamp, device_id=device_id, cpu_usage=data['cpu_usage']),
        BatteryPercentage(timestamp=timestamp, device_id=device_id, battery_percentage=data['battery_percentage']),
        IssLocation(timestamp=timestamp, latitude=data['iss_latitude'], longitude=data['iss_longitude'], location=data['iss_location'])
    ]
    
    db.session.bulk_save_objects(metrics)
    db.session.commit()
    print(f"Inserting metrics for device: {device_id}")
    
    # After storing metrics, emit to all connected clients
    socketio.emit('new_metrics', data)
    return jsonify({"message": "Metrics received and stored successfully"}), 200


@app.route('/api/metrics/latest', methods=['GET'])
def latest_metrics():
    device_id = request.args.get('device_id')  # Remove default value
    print(f"Fetching latest metrics for device: {device_id}")
    
    try:
        if device_id:
            # If device_id provided, filter by it
            latest_cpu = CpuUsage.query.filter_by(device_id=device_id).order_by(CpuUsage.timestamp.desc()).first()
            latest_battery = BatteryPercentage.query.filter_by(device_id=device_id).order_by(BatteryPercentage.timestamp.desc()).first()
        else:
            # If no device_id, get latest from any device
            latest_cpu = CpuUsage.query.order_by(CpuUsage.timestamp.desc()).first()
            if latest_cpu:
                device_id = latest_cpu.device_id
                latest_battery = BatteryPercentage.query.filter_by(device_id=device_id).order_by(BatteryPercentage.timestamp.desc()).first()
        
        latest_iss = IssLocation.query.order_by(IssLocation.timestamp.desc()).first()

        if latest_cpu and latest_battery and latest_iss:
            return jsonify({
                "device_id": device_id,
                "timestamp": latest_cpu.timestamp,
                "cpu_usage": latest_cpu.cpu_usage,
                "battery_percentage": latest_battery.battery_percentage,
                "iss_latitude": latest_iss.latitude,
                "iss_longitude": latest_iss.longitude,
                "iss_location": latest_iss.location
            })
        return jsonify({"error": "No data available"})
    except Exception as e:
        print(f"Error in latest_metrics: {str(e)}")
        return jsonify({"error": str(e)})

@app.route('/api/metrics/history', methods=['GET'])
def metrics_history():
    device_id = request.args.get('device_id')
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of records per page
    
    try:
        if not device_id:
            latest_record = CpuUsage.query.order_by(CpuUsage.timestamp.desc()).first()
            if latest_record:
                device_id = latest_record.device_id
            else:
                return jsonify({"items": [], "total_pages": 0})

        # Get total count for pagination
        total_records = CpuUsage.query.filter_by(device_id=device_id).count()
        total_pages = (total_records + per_page - 1) // per_page

        # Get paginated records
        cpu_metrics = CpuUsage.query.filter_by(device_id=device_id)\
            .order_by(CpuUsage.timestamp.desc())\
            .offset((page - 1) * per_page)\
            .limit(per_page)\
            .all()

        history = []
        for cpu in cpu_metrics:
            battery = BatteryPercentage.query.filter_by(device_id=device_id, timestamp=cpu.timestamp).first()
            iss = IssLocation.query.filter_by(timestamp=cpu.timestamp).first()
            
            if battery and iss:
                history.append({
                    "device_id": device_id,
                    "timestamp": cpu.timestamp,
                    "cpu_usage": cpu.cpu_usage,
                    "battery_percentage": battery.battery_percentage,
                    "iss_latitude": iss.latitude,
                    "iss_longitude": iss.longitude,
                    "iss_location": iss.location
                })

        return jsonify({
            "items": history,
            "total_pages": total_pages,
            "current_page": page
        })
    except Exception as e:
        print(f"Error in metrics_history: {str(e)}")
        return jsonify({"error": str(e)})

@app.route('/api/status')
def check_status():
    try:
        record_count = CpuUsage.query.count()
        return jsonify({
            "status": "ok",
            "record_count": record_count
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        })

@app.route('/api/command', methods=['POST'])
def receive_command():
    global latest_command
    data = request.json
    command = data.get('command')
    if not command:
        return jsonify({"error": "No command provided"}), 400
    latest_command = command
    return jsonify({"message": f"Command '{command}' sent successfully"})

@app.route('/api/command/check', methods=['GET'])
def check_command():
    global latest_command
    if latest_command:
        command = latest_command
        latest_command = None
        return jsonify({"command": command})
    return jsonify({"command": None})

@app.route('/api/devices', methods=['GET'])
def get_devices():
    try:
        # Get unique device IDs from CPU usage table
        devices = db.session.query(CpuUsage.device_id.distinct()).all()
        device_list = [device[0] for device in devices]
        return jsonify({"devices": device_list})
    except Exception as e:
        print(f"Error getting devices: {str(e)}")
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    socketio.run(app, debug=True)