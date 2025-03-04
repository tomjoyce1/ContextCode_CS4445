'''
Project brief : 
Monitors a range of system values from this computer (e.g battery, cpu usage)

Calls spacex api https://github.com/r-spacex/SpaceX-API and fetches 2 regularly chaning metrics

Publishes these metrics to a cloud platform (e.g pythonanywhere)

The cloud platform has a database of historical data

There is a frontend ui page which shows historical data from the db and current data

'''
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

def send_metrics_to_server(metrics):
    try:
        formatted_metrics = {
            "timestamp": metrics["timestamp"],
            "cpu_usage": float(metrics["cpu_usage"]),
            "battery_percentage": float(metrics["battery_percentage"]),
            "iss_latitude": float(metrics["iss_latitude"]),
            "iss_longitude": float(metrics["iss_longitude"]),
            "iss_location": str(metrics["iss_location"])
        }
                
        print("Attempting to send metrics:", json.dumps(metrics, indent=2))
        # Correctly formatted URL with proper protocol and host
        # url = 'https://tomjoyce.pythonanywhere.com/api/metrics'  
        url = 'http://127.0.0.1:5000/api/metrics'

        print(f"Sending request to: {url}")
        response = requests.post(url, json=metrics)
        print(f"Server response status code: {response.status_code}")
        print(f"Server response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Metrics successfully sent to server")
        else:
            print(f"❌ Failed to send metrics. Status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error sending metrics to server: {str(e)}")
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

            # Prepare combined metrics
            combined_metrics = {
                "timestamp": datetime.datetime.now().isoformat(),
                "cpu_usage": float(sys_metrics.get("cpu_usage", 0)),
                "battery_percentage": float(sys_metrics.get("battery_percentage", 0)),
                "iss_latitude": float(get_iss_data["latitude"]),
                "iss_longitude": float(get_iss_data["longitude"]),
                "iss_location": str(locationOnEarth)
            }

            print("\n4. Sending metrics to server...")
            send_metrics_to_server(combined_metrics)
            
            print('\nWaiting 20 secs before next update...\n')
            print('-' * 50)
            time.sleep(20)

        except Exception as e:
            print(f"❌ Error in main loop: {str(e)}")
            print("Stack trace:", e.__traceback__)
            time.sleep(10)

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

