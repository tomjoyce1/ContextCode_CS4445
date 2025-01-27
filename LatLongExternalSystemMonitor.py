import requests
import time
import EarthLocation

def get_iss_location():
    url = "http://api.open-notify.org/iss-now.json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return {
            "timestamp": data["timestamp"],
            "latitude": data["iss_position"]["latitude"],
            "longitude": data["iss_position"]["longitude"]
        }
    else:
        print(f"Error: {response.status_code}")
        return None


# Fetch the ISS location every second
# while True:
#     iss_data = get_iss_location()
#     if iss_data:
#         print(f"Timestamp: {iss_data['timestamp']}, Latitude: {iss_data['latitude']}, Longitude: {iss_data['longitude']}")
#     time.sleep(1)
