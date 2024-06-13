# uploads/file_watcher.py

import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import redis

WATCHED_DIR = '/tmp/test'
r = redis.Redis()

class UploadHandler(FileSystemEventHandler):
    def __init__(self, extension, queue_name):
        self.extension = extension
        self.queue_name = queue_name

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(self.extension):
            file_path = event.src_path
            study_info = {
                'path': file_path,
                'guid': os.path.basename(file_path),
                'InstanceUID': 'some_instance_uid',
                'timestamp': time.time(),  # Add timestamp
                'priority': 0,
                'status': 'queued'
            }
            r.zadd(self.queue_name, {str(study_info): 0})  # Default priority 0

def start_watcher(extension, queue_name):
    if not os.path.exists(WATCHED_DIR):
        os.makedirs(WATCHED_DIR)

    event_handler = UploadHandler(extension, queue_name)
    observer = Observer()
    observer.schedule(event_handler, WATCHED_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
