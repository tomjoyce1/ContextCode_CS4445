from geopy.geocoders import Nominatim

def get_location_from_coordinates(latitude, longitude):
    # Initialize geolocator
    geolocator = Nominatim(user_agent="thomasjoyceofficial@gmail.com")
    
    # Get location
    try:
        location = geolocator.reverse((latitude, longitude), exactly_one=True)
        if location:
            return location.address
        else:
            return "Location not found."
    except Exception as e:
        return f"An error occurred: {e}"

# Example ISS coordinates
# latitude = 41.4349  # Replace with ISS latitude
# longitude = 42.1661  # Replace with ISS longitude

# Get location
# location = get_location_from_coordinates(latitude, longitude)
# print(f"The location for Latitude {latitude}, Longitude {longitude} is: {location}")
