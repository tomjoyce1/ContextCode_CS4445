import psutil
import time
from datetime import datetime

def get_system_metrics():
    metrics = {
        'battery_percentage': None,
        'cpu_usage': psutil.cpu_percent(interval=1),
        'memory_usage': psutil.virtual_memory().percent,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        battery = psutil.sensors_battery()
        print(f"Debug - Battery object: {battery}")  # Debug print
        if battery is not None:
            print(f"Debug - Battery percent: {battery.percent}")  # Debug print
            print(f"Debug - Battery plugged in: {battery.power_plugged}")  # Debug print
            metrics['battery_percentage'] = battery.percent
        else:
            print("Debug - No battery detected")
    except Exception as e:
        print(f"Debug - Battery error: {str(e)}")
        
    return metrics
