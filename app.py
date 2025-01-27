from flask import Flask, request, jsonify, render_template
import sqlite3
import datetime

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('metrics.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS metrics (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   timestamp TEXT,
                   cpu_usage REAL,
                   battery_percentage REAL,
                   iss_latitude REAL,
                   iss_longitude REAL,
                   iss_location TEXT                  
                   )''')
    conn.commit()
    conn.close()

def store_data(data):
    conn = sqlite3.connect('metrics.db')
    cursor = conn.cursor()
    
    cursor.execute('''INSERT INTO metrics (timestamp, cpu_usage, battery_percentage, iss_latitude, iss_longitude, iss_location)
                   VALUES(?,?,?,?,?,?)''',                       
                   (data['timestamp'], data['cpu_usage'], data['battery_percentage'], 
                    data['iss_latitude'], data['iss_longitude'], data['iss_location']))
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/metrics', methods=['POST'])
def receive_metrics():
    data = request.json
    store_data(data)
    return jsonify({"message": "Metrics received and stored successfully"}), 200

@app.route('/api/metrics/latest', methods=['GET'])
def latest_metrics():
    conn = sqlite3.connect('metrics.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM metrics ORDER BY id DESC LIMIT 1')
    latest = cursor.fetchone()
    conn.close()
    if latest:
        return jsonify({
            "timestamp": latest[1],
            "cpu_usage": latest[2],
            "battery_percentage": latest[3],
            "iss_latitude": latest[4],
            "iss_longitude": latest[5],
            "iss_location": latest[6]
        })
    else:
        return jsonify({
                "timestamp": "",
                "cpu_usage": 0,
                "battery_percentage": 0,
                "iss_latitude": 0,
                "iss_longitude": 0,
                "iss_location": ""
            }), 200


@app.route('/api/metrics/history', methods=['GET'])
def metrics_history():
    conn = sqlite3.connect('metrics.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM metrics ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    history = [
        {
            "timestamp": row[1],
            "cpu_usage": row[2],
            "battery_percentage": row[3],
            "iss_latitude": row[4],
            "iss_longitude": row[5],
            "iss_location": row[6]
        }
        for row in rows
    ]
    return jsonify(history)

if __name__ == "__main__":
    init_db()  # Initialize the database before running the app
    app.run(debug=True)