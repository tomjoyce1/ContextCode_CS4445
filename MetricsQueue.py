from queue import Queue
import threading
import time
import requests
import json
from datetime import datetime

class QueuedMetric:
    def __init__(self, metrics, retry_count=0, next_retry=None):
        self.metrics = metrics
        self.retry_count = retry_count
        self.next_retry = next_retry

class MetricsQueue:
    def __init__(self, server_url='https://tomjoyce.pythonanywhere.com/api/metrics'):
        self.queue = Queue()
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.running = True
        self.server_url = server_url
        self.max_retries = 5
        self.base_delay = 2  # Base delay in seconds
        
    def start(self):
        print("Starting metrics queue worker...")
        self.worker_thread.start()
        
    def stop(self):
        print("Stopping metrics queue worker...")
        self.running = False
        self.worker_thread.join()
        
    def add_metrics(self, metrics):
        queued_metric = QueuedMetric(metrics)
        self.queue.put(queued_metric)
        print(f"Added metrics to queue. Queue size: {self.queue.qsize()}")
        
    def _calculate_next_retry(self, retry_count):
        # Exponential backoff: 2^retry_count seconds
        delay = self.base_delay * (2 ** retry_count)
        return datetime.now().timestamp() + delay
        
    def _process_queue(self):
        while self.running:
            try:
                if not self.queue.empty():
                    queued_metric = self.queue.get()
                    
                    # Check if it's time to retry
                    if queued_metric.next_retry and datetime.now().timestamp() < queued_metric.next_retry:
                        self.queue.put(queued_metric)  # Put it back if not ready
                        time.sleep(1)
                        continue
                    
                    success = self._send_metrics(queued_metric.metrics)
                    
                    if not success and queued_metric.retry_count < self.max_retries:
                        queued_metric.retry_count += 1
                        queued_metric.next_retry = self._calculate_next_retry(queued_metric.retry_count)
                        print(f"Retrying in {2 ** queued_metric.retry_count} seconds (attempt {queued_metric.retry_count}/{self.max_retries})")
                        self.queue.put(queued_metric)
                    elif not success:
                        print(f"Failed to send metrics after {self.max_retries} retries. Dropping data.")
                
                time.sleep(1)
            except Exception as e:
                print(f"Queue processing error: {e}")
                
    def _send_metrics(self, metrics):
        try:
            print(f"Attempting to send metrics to {self.server_url}")
            response = requests.post(self.server_url, json=metrics)
            
            if response.status_code == 200:
                print("✅ Metrics successfully sent")
                return True
            else:
                print(f"❌ Failed to send metrics. Status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending metrics: {str(e)}")
            return False
