import psutil
import time
from datetime import datetime

def get_system_metrics():
    metrics = {
        'battery_percent': psutil.sensors_battery().percent if psutil.sensors_battery() else None,
        'cpu_usage': psutil.cpu_percent(interval=1),
        'memory_usage': psutil.virtual_memory().percent,
        'timestamp': datetime.now().isoformat()
    }
    return metrics
