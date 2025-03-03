from flask import Flask, request, jsonify, render_template
from datetime import datetime
import sqlite3
import json
import os

app = Flask(__name__)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('metrics.db')
    c = conn.cursor()
    # Drop the table if it exists to fix the column order
    c.execute('DROP TABLE IF EXISTS metrics')
    c.execute('''CREATE TABLE IF NOT EXISTS metrics
                 (timestamp TEXT, 
                  cpu_usage REAL,
                  battery_percentage REAL, 
                  iss_latitude REAL, 
                  iss_longitude REAL, 
                  iss_location TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Store the latest command
latest_command = None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/metrics', methods=['POST'])
def receive_metrics():
    try:
        if not os.path.exists('metrics.db'):
            print("Database not found, initializing...")
            init_db()
        
        data = request.json
        print("Received data:", json.dumps(data, indent=2))
        
        # Validate data
        required_fields = ['timestamp', 'cpu_usage', 'battery_percentage', 
                         'iss_latitude', 'iss_longitude', 'iss_location']
        for field in required_fields:
            if field not in data:
                error_msg = f"Missing required field: {field}"
                print(error_msg)
                return jsonify({"error": error_msg}), 400
        
        try:
            # Test data conversion before DB insert
            float_values = {
                'cpu_usage': float(data['cpu_usage']),
                'battery_percentage': float(data['battery_percentage']),
                'iss_latitude': float(data['iss_latitude']),
                'iss_longitude': float(data['iss_longitude'])
            }
            print("Data conversion successful:", float_values)
        except ValueError as ve:
            error_msg = f"Data conversion error: {str(ve)}"
            print(error_msg)
            return jsonify({"error": error_msg}), 400

        try:
            conn = sqlite3.connect('metrics.db')
            c = conn.cursor()
            query = '''INSERT INTO metrics 
                      (timestamp, cpu_usage, battery_percentage, 
                       iss_latitude, iss_longitude, iss_location)
                      VALUES (?, ?, ?, ?, ?, ?)'''
            params = (data['timestamp'],
                     float_values['cpu_usage'],
                     float_values['battery_percentage'],
                     float_values['iss_latitude'],
                     float_values['iss_longitude'],
                     str(data['iss_location']))
            
            print("Executing SQL with params:", params)
            c.execute(query, params)
            conn.commit()
            conn.close()
            print("Database insert successful")
            return jsonify({"status": "success"})
        except sqlite3.Error as sqle:
            error_msg = f"Database error: {str(sqle)}"
            print(error_msg)
            return jsonify({"error": error_msg}), 500
            
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}\nType: {type(e)}"
        print(error_msg)
        import traceback
        print("Traceback:", traceback.format_exc())
        return jsonify({"error": error_msg}), 500

@app.route('/api/metrics/latest')
def get_latest_metrics():
    conn = sqlite3.connect('metrics.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM metrics ORDER BY timestamp DESC LIMIT 1''')
    row = c.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            "timestamp": row[0],
            "cpu_usage": row[1],
            "battery_percentage": row[2],
            "iss_latitude": row[3],
            "iss_longitude": row[4],
            "iss_location": row[5]
        })
    return jsonify({})

@app.route('/api/metrics/history')
def get_metrics_history():
    conn = sqlite3.connect('metrics.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM metrics ORDER BY timestamp DESC LIMIT 100''')
    rows = c.fetchall()
    conn.close()
    
    return jsonify([{
        "timestamp": row[0],
        "cpu_usage": row[1],
        "battery_percentage": row[2],
        "iss_latitude": row[3],
        "iss_longitude": row[4],
        "iss_location": row[5]
    } for row in rows])

# Add this route to check database status
@app.route('/api/status')
def check_status():
    try:
        if not os.path.exists('metrics.db'):
            return jsonify({
                "status": "error",
                "message": "Database file not found",
                "db_path": 'metrics.db'
            })
            
        conn = sqlite3.connect('metrics.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM metrics")
        count = c.fetchone()[0]
        conn.close()
        
        return jsonify({
            "status": "ok",
            "db_path": 'metrics.db',
            "record_count": count
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "db_path": 'metrics.db'
        })

@app.route('/api/command', methods=['POST'])
def receive_command():
    global latest_command
    try:
        data = request.json
        command = data.get('command')
        if not command:
            return jsonify({"error": "No command provided"}), 400
            
        # Store the command for the device to pick up
        latest_command = command
        return jsonify({"message": f"Command '{command}' sent successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/command/check', methods=['GET'])
def check_command():
    global latest_command
    if latest_command:
        command = latest_command
        latest_command = None  # Clear the command after it's retrieved
        return jsonify({"command": command})
    return jsonify({"command": None})

if __name__ == '__main__':
    app.run(debug=True)