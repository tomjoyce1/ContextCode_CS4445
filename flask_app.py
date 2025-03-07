from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import os
from config import Config
import time
import pymysql  # Required for MySQL
pymysql.install_as_MySQLdb()  # MySQL compatibility layer

def aware_utcnow():
    return datetime.now(timezone.utc)

def init_db():
    max_retries = 5
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            # Test MySQL connection
            conn = pymysql.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME
            )
            conn.close()
            print("Database connection successful")
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Database connection attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Failed to connect to database after multiple attempts")
                raise e

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database with retry logic
if init_db():
    db = SQLAlchemy(app)

class CpuUsage(db.Model):
    __tablename__ = 'cpu_usage'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)  # MySQL datetime
    cpu_usage = db.Column(db.Float(precision=5), nullable=False)
    
    __table_args__ = (
        db.Index('idx_cpu_device_time', 'device_id', 'timestamp'),
    )

class BatteryPercentage(db.Model):
    __tablename__ = 'battery_percentage'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)  # MySQL datetime
    battery_percentage = db.Column(db.Float(precision=5), nullable=False)
    
    __table_args__ = (
        db.Index('idx_battery_device_time', 'device_id', 'timestamp'),
    )

class IssLocation(db.Model):
    __tablename__ = 'iss_location'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, nullable=False)  # MySQL datetime
    latitude = db.Column(db.Float(precision=10), nullable=False)
    longitude = db.Column(db.Float(precision=10), nullable=False)
    location = db.Column(db.Text(length=1000), nullable=False)  # MySQL text with length
    
    __table_args__ = (
        db.Index('idx_iss_timestamp', 'timestamp'),
    )

with app.app_context():
    try:
        db.create_all()
        print('Checked database tables - created if not existing')
    except Exception as e:
        print(f"Error checking database tables: {e}")
        raise

latest_command = None

# api endpoints
@app.route('/')
def home():
    return render_template('index.html')

# Aggregator api
# Receives a POST request with CPU, battery, and ISS data.
# Parses the timestamp and stores all metrics in the database.

@app.route('/api/metrics', methods=['POST'])
def receive_metrics():
    data = request.json
    device_id = data.get('device_id', 'unknown_device')
    timestamp = datetime.strptime(data['timestamp'], '%Y-%m-%dT%H:%M:%S.%f')

    metrics = [
        CpuUsage(timestamp=timestamp, device_id=device_id, cpu_usage=data['cpu_usage']),
        BatteryPercentage(timestamp=timestamp, device_id=device_id, battery_percentage=data['battery_percentage']),
        IssLocation(timestamp=timestamp, latitude=data['iss_latitude'], longitude=data['iss_longitude'], location=data['iss_location'])
    ]
    
    db.session.bulk_save_objects(metrics)
    db.session.commit()
    print(f"Inserting metrics for device: {device_id}")
    
    return jsonify({"message": "Metrics received and stored successfully"}), 200

@app.route('/api/metrics/latest', methods=['GET'])
def latest_metrics():
    device_id = request.args.get('device_id')
    print(f"Fetching latest metrics for device: {device_id}")
    
    try:
        if device_id:
            latest_cpu = CpuUsage.query.filter_by(device_id=device_id).order_by(CpuUsage.timestamp.desc()).first()
            latest_battery = BatteryPercentage.query.filter_by(device_id=device_id).order_by(BatteryPercentage.timestamp.desc()).first()
        else:
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
    per_page = 10
    
    try:
        query = CpuUsage.query
        if device_id:  # If specific device selected
            query = query.filter_by(device_id=device_id)
            
        total_records = query.count()
        total_pages = (total_records + per_page - 1) // per_page

        # Get paginated records for all or specific device
        cpu_metrics = query.order_by(CpuUsage.timestamp.desc())\
            .offset((page - 1) * per_page)\
            .limit(per_page)\
            .all()

        history = []
        for cpu in cpu_metrics:
            # Match battery data by device_id and timestamp
            battery = BatteryPercentage.query.filter_by(
                device_id=cpu.device_id, 
                timestamp=cpu.timestamp
            ).first()
            
            # Match ISS data by timestamp only
            iss = IssLocation.query.filter_by(timestamp=cpu.timestamp).first()
            
            if battery and iss:
                history.append({
                    "device_id": cpu.device_id,
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
        devices = db.session.query(CpuUsage.device_id.distinct()).all()
        device_list = [device[0] for device in devices]
        return jsonify({"devices": device_list})
    except Exception as e:
        print(f"Error getting devices: {str(e)}")
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(debug=True)