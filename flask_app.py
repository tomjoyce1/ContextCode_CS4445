from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import os

def aware_utcnow():
    return datetime.now(timezone.utc)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///metricdatabase.db'  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Timestamp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=aware_utcnow)

class CpuUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp_id = db.Column(db.Integer, db.ForeignKey('timestamp.id'), nullable=False)
    cpu_usage = db.Column(db.Float, nullable=False)

class BatteryPercentage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp_id = db.Column(db.Integer, db.ForeignKey('timestamp.id'), nullable=False)
    battery_percentage = db.Column(db.Float, nullable=False)

class IssLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp_id = db.Column(db.Integer, db.ForeignKey('timestamp.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    location = db.Column(db.String, nullable=False)

with app.app_context():
    db.create_all()

latest_command = None  # Define the global variable

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/metrics', methods=['POST'])
def receive_metrics():
    data = request.json
    timestamp = Timestamp(timestamp=datetime.strptime(data['timestamp'], '%Y-%m-%dT%H:%M:%S.%f'))
  # Provide format string
    db.session.add(timestamp)
    db.session.flush()

    metrics = [
        CpuUsage(timestamp_id=timestamp.id, cpu_usage=data['cpu_usage']),
        BatteryPercentage(timestamp_id=timestamp.id, battery_percentage=data['battery_percentage']),
        IssLocation(timestamp_id=timestamp.id, latitude=data['iss_latitude'], longitude=data['iss_longitude'], location=data['iss_location'])
    ]
    db.session.bulk_save_objects(metrics)
    db.session.commit()

    return jsonify({"message": "Metrics received and stored successfully"}), 200

@app.route('/api/metrics/latest', methods=['GET'])
def latest_metrics():
        latest = db.session.query(
        Timestamp.timestamp, CpuUsage.cpu_usage, 
        BatteryPercentage.battery_percentage, 
        IssLocation.latitude, IssLocation.longitude, IssLocation.location
    ).join(CpuUsage, CpuUsage.timestamp_id == Timestamp.id) \
     .join(BatteryPercentage, BatteryPercentage.timestamp_id == Timestamp.id) \
     .join(IssLocation, IssLocation.timestamp_id == Timestamp.id) \
     .order_by(Timestamp.id.desc()).first()

        if latest:
            return jsonify({
                    "timestamp": latest.timestamp,
                    "cpu_usage": latest.cpu_usage,
                    "battery_percentage": latest.battery_percentage,
                    "iss_latitude": latest.latitude,
                    "iss_longitude": latest.longitude,
                    "iss_location": latest.location
                })
    
        return jsonify({})

@app.route('/api/metrics/history', methods=['GET'])
def metrics_history():
    history = []
    timestamps = Timestamp.query.order_by(Timestamp.id.desc()).limit(100).all()
    for timestamp in timestamps:
        cpu_usage = CpuUsage.query.filter_by(timestamp_id=timestamp.id).first()
        battery_percentage = BatteryPercentage.query.filter_by(timestamp_id=timestamp.id).first()
        iss_location = IssLocation.query.filter_by(timestamp_id=timestamp.id).first()
        history.append({
            "timestamp": timestamp.timestamp,
            "cpu_usage": cpu_usage.cpu_usage,
            "battery_percentage": battery_percentage.battery_percentage,
            "iss_latitude": iss_location.latitude,
            "iss_longitude": iss_location.longitude,
            "iss_location": iss_location.location
        })
    return jsonify(history)

@app.route('/api/status')
def check_status():
    try:
        record_count = Timestamp.query.count()
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



if __name__ == '__main__':
    app.run(debug=True)