from geopy.geocoders import Nominatim
import os
from dotenv import load_dotenv

load_dotenv()
USER_AGENT = os.getenv('USER_AGENT', 'default_user_agent')

# Reverse geocoding
def get_location_from_coordinates(latitude, longitude):
    geolocator = Nominatim(user_agent=USER_AGENT)
    try:
        location = geolocator.reverse((latitude, longitude), exactly_one=True)
        if location:
            return location.address
        else:
            return "Location not found."
    except Exception as e:
        return f"An error occurred: {e}"
