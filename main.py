import psutil
import LocalComputerSystemMonitor
import LatLongExternalSystemMonitor
import time
import EarthLocation
import requests
import datetime
import json
import os
import sys
from MetricsQueue import MetricsQueue
import socket

metrics_queue = MetricsQueue('https://tomjoyce.pythonanywhere.com/api/metrics')  

# def get_device_id():
#     return socket.gethostname()

def get_device_id():
    return os.getenv('DEVICE_ID', socket.gethostname())

def send_metrics_to_server(metrics):
    # added to the queue
    # Worker thread sends to server as JSON request
    metrics_queue.add_metrics(metrics)

def check_for_commands():
    try:
        print("\nChecking for commands...")
        url = 'https://tomjoyce.pythonanywhere.com/api/command/check'
        response = requests.get(url)
        print(f"Command check response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            command = data.get('command')
            print(f"Command received: {command}")
            
            if command == 'restart':
                print("🔄 Restart command received!")
                print("Initiating restart sequence...")
                print("3...")
                time.sleep(1)
                print("2...")
                time.sleep(1)
                print("1...")
                time.sleep(1)
                print("Restarting now! 🚀")
                os.execv(sys.executable, ['python'] + sys.argv)  
            elif command:
                print(f"Unknown command received: {command}")
        else:
            print(f"Command check failed with status code: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error checking for commands: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print("Stack trace:", traceback.format_exc())


def main():
    # Start the queue worker
    metrics_queue.start()
    device_id = get_device_id()
    print(f"Device ID: {device_id}")
    
    try:
        while True:
            try:
                # Check for commands first
                print("\nChecking for commands...")
                check_for_commands()

                # Collect local computer metrics
                print("\n1. Collecting local system metrics...")
                sys_metrics = LocalComputerSystemMonitor.get_system_metrics()
                if not sys_metrics:
                    print("❌ Local system metrics failed")
                    continue
                print("✅ Local metrics collected:", sys_metrics)

                # Collect ISS location data
                print("\n2. Collecting ISS location data...")
                get_iss_data = LatLongExternalSystemMonitor.get_iss_location()
                if get_iss_data is None:
                    print("❌ Failed to get ISS location data")
                    continue
                print("✅ ISS data collected:", get_iss_data)

                print("\n3. Getting Earth location...")
                locationOnEarth = EarthLocation.get_location_from_coordinates(
                    get_iss_data["latitude"], 
                    get_iss_data["longitude"]
                )
                print("✅ Earth location determined:", locationOnEarth)

                # dictionary sent on as json payload
                combined_metrics = {
                    "device_id": device_id,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "cpu_usage": float(sys_metrics.get("cpu_usage", 0)),
                    "battery_percentage": float(sys_metrics.get("battery_percentage", 0)),
                    "iss_latitude": float(get_iss_data["latitude"]),
                    "iss_longitude": float(get_iss_data["longitude"]),
                    "iss_location": str(locationOnEarth)
                }

                print("\n4. Queueing metrics for sending...")
                send_metrics_to_server(combined_metrics)
                
                print('\nWaiting 20 secs before next update...\n')
                print('-' * 50)
                time.sleep(20)

            except Exception as e:
                print(f"❌ Error in main loop: {str(e)}")
                time.sleep(10)

    except KeyboardInterrupt:
        print("\nStopping metrics queue...")
        metrics_queue.stop()
        print("Exiting gracefully...")
    except Exception as e:
        metrics_queue.stop()
        print(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    print("Starting metrics collection...")
    print("Press Ctrl+C to exit")
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        raise

