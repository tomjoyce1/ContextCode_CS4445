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
def main():
    
    while True:
        try:
            # Collect local pc metrics
            sys_metrics = LocalComputerSystemMonitor.get_system_metrics()
            if sys_metrics:
                print("Current system metrics:", sys_metrics)
            else:
                print("Local system metrics failed")   


            # Collect 3rd party metrics

            get_iss_data = LatLongExternalSystemMonitor.get_iss_location()
            print("Current system metrics:", get_iss_data)   


            if get_iss_data is not None:
                locationOnEarth = EarthLocation.get_location_from_coordinates(
                    get_iss_data["latitude"], 
                    get_iss_data["longitude"]
                    )

                print("Current system metrics:", get_iss_data, locationOnEarth)   
                print('waiting 20 secs...')
                time.sleep(20)  
       
            else:
                print("failed to get iss loc data")
                time.sleep(20)  
    


        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(10)  

if __name__ == "__main__":
    main()


